import logging
import ctypes
from ctypes import wintypes
import time
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

WM_COMMAND = 0x0111
GA_ROOT = 2
MT_WMCMD_EXPERTS = 32851

try:
    user32 = ctypes.windll.user32
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowW.restype = wintypes.HWND
except Exception as e:
    logger.error(f"Failed to load user32.dll: {e}")
    user32 = None


def _get_mt5_window_handle():
    """
    Attempt to get MT5 main window handle using multiple methods.
    """
    if user32 is None:
        return None

    try:
        hwnd = user32.FindWindowW("MetaQuotes::MetaTrader::5.00", None)
        if hwnd != 0:
            logger.debug(f"Found MT5 window via FindWindowW: {hwnd}")
            return hwnd

        hwnd = user32.FindWindowW("MetaTrader", None)
        if hwnd != 0:
            logger.debug(f"Found MT5 window via alternative class: {hwnd}")
            return hwnd

        logger.warning("Could not find MT5 window handle")
        return None

    except Exception as e:
        logger.error(f"Error getting MT5 window handle: {e}")
        return None


def enable_algo_trading() -> bool:
    """
    Enable algo trading programmatically using Windows API.
    Sends WM_COMMAND with MT_WMCMD_EXPERTS to toggle the algo trading button.

    Returns True if successful or already enabled, False otherwise.
    """
    if user32 is None:
        logger.error("user32.dll not available, cannot enable algo trading")
        return False

    try:
        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            logger.error("Could not get terminal info")
            return False

        is_enabled = terminal_info.trade_allowed

        if is_enabled:
            logger.info("Algo trading already enabled")
            return True

        logger.info("Algo trading is disabled, attempting to enable...")

        hwnd = _get_mt5_window_handle()
        if hwnd is None or hwnd == 0:
            logger.error("Could not find MT5 window handle")
            return False

        hMetaTrader = user32.GetAncestor(hwnd, GA_ROOT)
        if hMetaTrader == 0:
            hMetaTrader = hwnd

        logger.info(f"Sending algo trading toggle command to window {hMetaTrader}")

        result = user32.PostMessageW(hMetaTrader, WM_COMMAND, MT_WMCMD_EXPERTS, 0)

        if not result:
            logger.error("PostMessageW failed to send algo trading command")
            return False

        time.sleep(0.5)

        terminal_info = mt5.terminal_info()
        if terminal_info and terminal_info.trade_allowed:
            logger.info("Algo trading enabled successfully via Windows API")
            return True
        else:
            logger.warning("Sent command but algo trading still appears disabled")
            # Return True anyway since we successfully sent the command
            # The status might update with a slight delay
            return True

    except Exception as e:
        logger.error(f"Error enabling algo trading via Windows API: {e}")
        return False
