import base64
import ctypes
import io
import sys
import subprocess
import tempfile
from pathlib import Path
from ctypes import wintypes

from PIL import Image, ImageGrab


def enable_dpi_awareness() -> None:
    """Make Win32 coordinates match physical pixels on scaled displays."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


class _MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


def _cursor_monitor_bbox() -> tuple[int, int, int, int] | None:
    try:
        user32 = ctypes.windll.user32
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
        user32.MonitorFromPoint.restype = wintypes.HMONITOR
        hmon = user32.MonitorFromPoint(pt, 2)  # MONITOR_DEFAULTTONEAREST
        info = _MonitorInfo(cbSize=ctypes.sizeof(_MonitorInfo))
        if not user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            return None
        r = info.rcMonitor
        return (r.left, r.top, r.right, r.bottom)
    except (AttributeError, OSError):
        return None


def grab_screen() -> Image.Image:
    """Screenshot the monitor the mouse cursor is on."""
    if sys.platform == "darwin":
        return _grab_mac_screen()
    bbox = _cursor_monitor_bbox()
    if bbox:
        return ImageGrab.grab(bbox=bbox, all_screens=True)
    return ImageGrab.grab()


def to_jpeg_b64(image: Image.Image, max_edge: int) -> str:
    image = image.convert("RGB")
    if max(image.size) > max_edge:
        image.thumbnail((max_edge, max_edge), Image.BICUBIC)
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def mac_screen_permission(request: bool = False) -> bool:
    if sys.platform != "darwin":
        return True
    import Quartz
    if Quartz.CGPreflightScreenCaptureAccess():
        return True
    if request:
        return bool(Quartz.CGRequestScreenCaptureAccess())
    return False


def _mac_monitor_bbox() -> tuple[int, int, int, int]:
    import Quartz
    point = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
    error, displays, count = Quartz.CGGetActiveDisplayList(32, None, None)
    if error:
        raise RuntimeError("Cannot read the connected displays.")
    selected = Quartz.CGMainDisplayID()
    for display in displays[:count]:
        rect = Quartz.CGDisplayBounds(display)
        if (rect.origin.x <= point.x < rect.origin.x + rect.size.width
                and rect.origin.y <= point.y < rect.origin.y + rect.size.height):
            selected = display
            break
    rect = Quartz.CGDisplayBounds(selected)
    return tuple(int(v) for v in (rect.origin.x, rect.origin.y, rect.size.width, rect.size.height))


def _grab_mac_screen() -> Image.Image:
    if not mac_screen_permission():
        raise RuntimeError("Allow Screen Recording for Terminal in System Settings > Privacy & Security. Then restart Terminal.")
    region = ",".join(map(str, _mac_monitor_bbox()))
    with tempfile.TemporaryDirectory(prefix="answerwrite-") as folder:
        target = Path(folder) / "screen.png"
        result = subprocess.run(
            ["/usr/sbin/screencapture", "-x", "-R" + region, str(target)],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode or not target.exists():
            raise RuntimeError("Screen capture failed. Check Screen Recording permission and restart Terminal.")
        with Image.open(target) as image:
            return image.copy()
