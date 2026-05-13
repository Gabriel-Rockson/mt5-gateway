"""
Broker timezone detection and translation.

MT5 emits Unix timestamps that decode to broker server local wallclock — i.e.,
the integer corresponds to the broker's clock readings interpreted as if it were
UTC. To present a consistent real-UTC interface to downstream consumers, this
module identifies the broker's IANA timezone and exposes `to_real_utc` /
`from_real_utc` conversion helpers.

Two sources for the timezone, in order of authority:
  1. BROKER_TIMEZONE env var (e.g. "Europe/Athens"). When set, this is the
     active timezone immediately at startup — no race window on first
     requests.
  2. A background probe of `symbol_info_tick`. Used to detect the offset when
     the env var is not set, and as a sanity check that surfaces config drift
     when it is set (logs a warning on disagreement; env still wins).
"""

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Union
from zoneinfo import ZoneInfo

import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

# Brokers we've encountered or are likely to. If the probed offset matches one
# of these zones *now*, we use the IANA name so DST is honored. Otherwise we
# fall back to a fixed-offset Etc/GMT zone.
KNOWN_ZONES = [
    "UTC",
    "Europe/Athens",
    "Europe/London",
    "America/New_York",
    "Asia/Tokyo",
    "Asia/Hong_Kong",
    "Australia/Sydney",
]

REFRESH_INTERVAL_S = 15 * 60
INITIAL_DELAY_S = 5             # let MT5 come up before first probe
PER_CANDIDATE_POLL_S = 3        # poll each candidate up to this long
PER_CANDIDATE_INTERVAL_S = 0.5
MAX_PROBE_CANDIDATES = 5        # cap attempts so a quiet symbol list doesn't stall


def _find_probe_symbols() -> list:
    """
    Return an ordered list of candidate symbols for clock probing. Different
    brokers rename instruments with suffixes (`EURUSD.r`, `EURUSDm`, `EURUSD.cash`),
    so we enumerate the broker's actual symbol catalog rather than hardcoding
    one name. EUR-prefixed forex pairs are the most universally liquid 24/5
    candidates; we prefer something resembling EURUSD specifically.
    """
    candidates: list = []
    env_sym = os.environ.get("BROKER_PROBE_SYMBOL", "").strip()
    if env_sym:
        candidates.append(env_sym)
    try:
        all_syms = mt5.symbols_get() or []
    except Exception as e:
        logger.warning(f"broker clock: symbols_get failed: {e}")
        return candidates

    # Pass 1: names that begin with EURUSD (covers EURUSD, EURUSD.r, EURUSDm, etc).
    for s in all_syms:
        if s.name.upper().startswith("EURUSD") and s.name not in candidates:
            candidates.append(s.name)
    # Pass 2: any other EUR-prefixed forex pair (length ≥ 6 to exclude indices like EURO50).
    for s in all_syms:
        nm = s.name.upper()
        if nm.startswith("EUR") and len(s.name) >= 6 and s.name not in candidates:
            candidates.append(s.name)
    return candidates


def _map_offset_to_zone(offset_seconds: int) -> str:
    # Must be tz-aware: ZoneInfo.utcoffset() returns None for naive datetimes.
    now = datetime.now(tz=timezone.utc)
    for tz_name in KNOWN_ZONES:
        off = ZoneInfo(tz_name).utcoffset(now)
        if off is not None and int(off.total_seconds()) == offset_seconds:
            return tz_name
    if offset_seconds == 0:
        return "UTC"
    hours = offset_seconds // 3600
    if hours * 3600 == offset_seconds:
        # Etc/GMT signs are inverted: Etc/GMT-3 is UTC+3.
        return f"Etc/GMT{'-' if hours > 0 else '+'}{abs(hours)}"
    return "UTC"


class BrokerClock:
    def __init__(self, env_timezone: Optional[str] = None):
        self._lock = threading.Lock()
        # Empty string env var is the same as unset.
        self._env_timezone: Optional[str] = env_timezone or None
        initial = self._env_timezone or "UTC"
        self._timezone: str = initial
        self._zone_obj: Optional[ZoneInfo] = None if initial == "UTC" else ZoneInfo(initial)

        if self._env_timezone:
            logger.info(
                f"broker clock pinned to {self._env_timezone} via BROKER_TIMEZONE env var"
            )
        else:
            logger.info(
                "broker clock: no BROKER_TIMEZONE env set; will rely on background probe"
            )

        # Background daemon thread keeps the timezone in sync without blocking requests.
        self._probe_thread = threading.Thread(
            target=self._probe_loop, daemon=True, name="broker-clock-probe"
        )
        self._probe_thread.start()

    @property
    def timezone(self) -> str:
        return self._timezone

    @property
    def zone(self) -> Optional[ZoneInfo]:
        return self._zone_obj

    def _probe_loop(self) -> None:
        time.sleep(INITIAL_DELAY_S)
        while True:
            try:
                self._probe_once()
            except Exception as e:
                logger.warning(f"broker clock probe loop error: {e}")
            time.sleep(REFRESH_INTERVAL_S)

    def _probe_once(self) -> None:
        candidates = _find_probe_symbols()
        if not candidates:
            logger.warning(
                "broker clock probe: no usable symbol found in broker's symbols_get() catalog"
            )
            return

        used_symbol = None
        tick_time = 0
        for symbol in candidates[:MAX_PROBE_CANDIDATES]:
            try:
                mt5.symbol_select(symbol, True)
            except Exception as e:
                logger.debug(f"broker clock probe: symbol_select({symbol}) failed: {e}")
                continue
            # Short poll per candidate — quiet symbols get skipped quickly.
            deadline = time.time() + PER_CANDIDATE_POLL_S
            while time.time() < deadline:
                try:
                    tick = mt5.symbol_info_tick(symbol)
                except Exception:
                    tick = None
                if tick is not None and getattr(tick, "time", 0):
                    tick_time = int(tick.time)
                    used_symbol = symbol
                    break
                time.sleep(PER_CANDIDATE_INTERVAL_S)
            if tick_time:
                break

        if not tick_time:
            logger.warning(
                f"broker clock probe: no tick from any of {candidates[:MAX_PROBE_CANDIDATES]}"
            )
            return

        # Snap to 15-min grid to absorb network jitter.
        offset = round((tick_time - int(time.time())) / 900) * 900
        detected = _map_offset_to_zone(offset)

        with self._lock:
            if self._env_timezone:
                if detected != self._env_timezone:
                    logger.warning(
                        f"broker clock probe disagrees with BROKER_TIMEZONE env: "
                        f"probe detected {detected} (offset {offset:+}s, via {used_symbol}), "
                        f"env is {self._env_timezone}. "
                        f"Keeping env value — fix the env or investigate the broker server config."
                    )
                else:
                    logger.info(f"broker clock probe confirmed {detected} (via {used_symbol})")
            else:
                if detected != self._timezone:
                    logger.info(
                        f"broker clock probe detected: offset={offset:+}s "
                        f"({offset/3600:+.1f}h) → {detected} (was {self._timezone}, via {used_symbol})"
                    )
                    self._timezone = detected
                    self._zone_obj = None if detected == "UTC" else ZoneInfo(detected)

    # Fields that hold seconds since epoch.
    _SEC_FIELDS = ("time", "time_setup", "time_done", "time_expiration", "time_update")
    # Fields that hold milliseconds since epoch.
    _MSEC_FIELDS = ("time_msc", "time_setup_msc", "time_done_msc", "time_update_msc")

    def normalize_mt5_dict(self, d: dict) -> dict:
        """In-place: rewrite MT5 broker-time fields to real-UTC equivalents."""
        for f in self._SEC_FIELDS:
            v = d.get(f)
            if v:
                d[f] = self.to_real_utc(v)
        for f in self._MSEC_FIELDS:
            v = d.get(f)
            if v:
                # Preserve millisecond precision while shifting the seconds part.
                d[f] = self.to_real_utc(v // 1000) * 1000 + (v % 1000)
        return d

    def to_real_utc(self, broker_epoch: Optional[Union[int, float]]) -> Optional[int]:
        """Convert MT5 broker-wallclock-as-UTC epoch → real UTC epoch."""
        if broker_epoch is None:
            return None
        zone = self._zone_obj
        if zone is None:
            return int(broker_epoch)
        # The raw epoch decodes to broker wallclock when interpreted as UTC.
        naive_broker = datetime.utcfromtimestamp(int(broker_epoch))
        aware_broker = naive_broker.replace(tzinfo=zone)
        return int(aware_broker.astimezone(timezone.utc).timestamp())

    def from_real_utc(self, real_epoch: Optional[Union[int, float]]) -> Optional[int]:
        """Convert real UTC epoch → broker-wallclock-as-UTC epoch (for MT5 SDK input)."""
        if real_epoch is None:
            return None
        zone = self._zone_obj
        if zone is None:
            return int(real_epoch)
        real_dt = datetime.fromtimestamp(int(real_epoch), tz=timezone.utc)
        broker_wallclock = real_dt.astimezone(zone)
        # Re-stamp the wallclock as if it were UTC, then take its epoch.
        return int(broker_wallclock.replace(tzinfo=timezone.utc).timestamp())

    def vectorized_to_real_utc(self, epoch_series):
        """
        Vectorized conversion for bulk bar data — uses pandas tz_localize/tz_convert
        which is implemented in C. Handles DST transitions correctly.

        Input: pandas Series of int64 epoch seconds (broker-wallclock-as-UTC).
        Output: pandas Series of int64 epoch seconds in real UTC.
        """
        import pandas as pd

        tz_name = self._timezone
        if tz_name == "UTC":
            return epoch_series
        ts = pd.to_datetime(epoch_series, unit="s")
        # Pass the timezone name (string) — pandas 1.4 does not accept ZoneInfo objects.
        return ts.dt.tz_localize(tz_name).dt.tz_convert("UTC").astype("int64") // 10**9


# Singleton.
broker_clock = BrokerClock(env_timezone=os.environ.get("BROKER_TIMEZONE", "").strip() or None)
