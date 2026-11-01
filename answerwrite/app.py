import logging
import threading
import time

import sys
import signal

from .hotkeys import GlobalHotkey

from .capture import enable_dpi_awareness, grab_screen, to_jpeg_b64, mac_screen_permission
from .config import Config, load_config
from .popup import Popup
from .providers import OllamaProvider, Provider, make_provider

logger = logging.getLogger("answerwrite")


class AnswerWrite:
    def __init__(self, cfg: Config, provider: Provider, popup: Popup):
        self.cfg = cfg
        self.provider = provider
        self.popup = popup
        self._busy = threading.Lock()

    def on_hotkey(self) -> None:
        threading.Thread(target=self._handle, daemon=True).start()

    def _handle(self) -> None:
        if not self._busy.acquire(blocking=False):
            return
        try:
            # Keep our own popup out of the screenshot
            self.popup.hide(wait=True)
            time.sleep(0.08)
            image = grab_screen()
            self.popup.show("Thinking...", seconds=0)

            started = time.perf_counter()
            answer = self.provider.answer(to_jpeg_b64(image, self.cfg.max_image_edge))
            logger.info("Answer in %.1fs: %s", time.perf_counter() - started, answer)
            self.popup.show(answer or "(empty response)")
        except Exception as exc:
            logger.exception("Hotkey handler failed")
            self.popup.show(f"Error: {exc}")
        finally:
            self._busy.release()


def _warm_up(provider: OllamaProvider) -> None:
    try:
        provider.warm_up()
        logger.info("Ollama model %s loaded", provider.model)
    except Exception as exc:
        logger.warning("Ollama warm-up failed: %s", exc)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    enable_dpi_awareness()
    cfg = load_config()
    if sys.platform == "darwin":
        import ApplicationServices
        if not ApplicationServices.AXIsProcessTrusted():
            ApplicationServices.AXIsProcessTrustedWithOptions({ApplicationServices.kAXTrustedCheckOptionPrompt: True})
            raise SystemExit("Allow Terminal (or your launcher app) in System Settings > Privacy & Security > Accessibility. Then restart it.")
        if not mac_screen_permission(request=True):
            raise SystemExit("Allow Terminal (or your launcher app) in System Settings > Privacy & Security > Screen Recording. Then restart it.")
    provider = make_provider(cfg)
    popup = Popup(cfg.popup_seconds)
    app = AnswerWrite(cfg, provider, popup)

    if isinstance(provider, OllamaProvider):
        threading.Thread(target=_warm_up, args=(provider,), daemon=True).start()

    hotkey = GlobalHotkey(cfg.hotkey, app.on_hotkey)
    hotkey.start()
    signal.signal(signal.SIGINT, lambda *_: popup.quit())
    signal.signal(signal.SIGTERM, lambda *_: popup.quit())
    logger.info("Using %s (%s). Press %s to answer, Ctrl+C to quit.", cfg.provider, cfg.model, cfg.hotkey)
    popup.show(f"Ready ({cfg.provider}: {cfg.model}). Press {cfg.hotkey} to answer.")
    try:
        popup.run()
    except KeyboardInterrupt:
        pass
    finally:
        hotkey.stop()
        popup.close()
