"""
Broker timezone detection and translation.

MT5 emits Unix timestamps that decode to broker server local wallclock — i.e.,
the integer corresponds to the broker's clock readings interpreted as if it were
UTC. To present a consistent real-UTC interface to downstream consumers, this
module detects the broker's IANA timezone by probing `symbol_info_tick` and
exposes `to_real_utc` / `from_real_utc` conversion helpers.

The probe runs lazily on first access and re-runs every REFRESH_INTERVAL_S so
DST transitions are picked up without requiring a process restart.
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
PROBE_SYMBOL = "XAUUSD"


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
    def __init__(self, fallback_timezone: str = "UTC"):
        self._lock = threading.Lock()
        self._fallback = fallback_timezone
        self._timezone = fallback_timezone
        self._zone_obj: Optional[ZoneInfo] = None if fallback_timezone == "UTC" else ZoneInfo(fallback_timezone)
        self._last_probed_at = 0.0

    @property
    def timezone(self) -> str:
        if time.time() - self._last_probed_at > REFRESH_INTERVAL_S:
            self._probe()
        return self._timezone

    @property
    def zone(self) -> Optional[ZoneInfo]:
        """Cached ZoneInfo for the current broker zone (None if UTC)."""
        if time.time() - self._last_probed_at > REFRESH_INTERVAL_S:
            self._probe()
        return self._zone_obj

    def _probe(self) -> None:
        with self._lock:
            if time.time() - self._last_probed_at <= REFRESH_INTERVAL_S:
                return
            try:
                tick = mt5.symbol_info_tick(PROBE_SYMBOL)
                if tick is None or not getattr(tick, "time", None):
                    raise RuntimeError(f"no tick for {PROBE_SYMBOL}")
                real_now = int(time.time())
                delta = int(tick.time) - real_now
                # Snap to 15-min grid to absorb network jitter.
                offset = round(delta / 900) * 900
                detected = _map_offset_to_zone(offset)
                if detected != self._timezone:
                    logger.info(
                        f"broker clock detected: offset={offset:+}s "
                        f"({offset/3600:+.1f}h) → {detected} "
                        f"(was {self._timezone})"
                    )
                self._timezone = detected
                self._zone_obj = None if detected == "UTC" else ZoneInfo(detected)
                self._last_probed_at = time.time()
            except Exception as e:
                logger.warning(
                    f"broker clock probe failed, keeping {self._timezone}: {e}"
                )
                # Back off briefly so we don't hammer on persistent failure.
                self._last_probed_at = time.time() - REFRESH_INTERVAL_S + 60

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
        zone = self.zone
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
        zone = self.zone
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

        tz_name = self.timezone
        if tz_name == "UTC":
            return epoch_series
        ts = pd.to_datetime(epoch_series, unit="s")
        # Localize as broker-time, then convert to real UTC. Pass the timezone name
        # (string) — pandas 1.4 does not accept ZoneInfo objects directly.
        return ts.dt.tz_localize(tz_name).dt.tz_convert("UTC").astype("int64") // 10**9


# Singleton — env var lets ops force a specific zone when the probe is unreliable
# (e.g., market closed on first boot).
broker_clock = BrokerClock(
    fallback_timezone=os.environ.get("BROKER_TIMEZONE", "UTC")
)
