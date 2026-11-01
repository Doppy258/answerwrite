import queue
import threading
import sys
import tkinter as tk


class Popup:
    """A single borderless always-on-top toast owned by the Tk main thread.

    Other threads call show()/hide(); requests are queued and applied by Tk.
    """

    def __init__(self, default_seconds: float):
        self.default_seconds = default_seconds
        self._queue: queue.Queue = queue.Queue()
        self._hide_job = None

        self.root = tk.Tk()
        self.root.title("AnswerWrite Overlay")
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.45)
        self.label = tk.Label(
            self.root,
            bg="#222",
            fg="#f2f2f2",
            padx=8,
            pady=4,
            font=("Helvetica" if sys.platform == "darwin" else "Segoe UI", 13),
            justify="left",
            wraplength=520,
        )
        self.label.pack()
        self.label.bind("<Button-1>", lambda _e: self._hide())
        self.root.after(50, self._drain)

    # Thread-safe API

    def show(self, message: str, seconds: float | None = None) -> None:
        """Show a message; seconds=0 keeps it up until replaced or hidden."""
        self._queue.put(("show", message, seconds))

    def hide(self, wait: bool = False) -> None:
        done = threading.Event() if wait else None
        self._queue.put(("hide", done, None))
        if done is not None and not done.wait(2):
            raise RuntimeError("The popup did not hide before screen capture.")

    def quit(self) -> None:
        self.root.quit()

    def close(self) -> None:
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()

    # Tk-thread internals

    def _drain(self) -> None:
        try:
            while True:
                action, message, seconds = self._queue.get_nowait()
                if action == "show":
                    self._show(message, seconds)
                else:
                    self._hide()
                    if message is not None:
                        message.set()
        except queue.Empty:
            pass
        self.root.after(50, self._drain)

    def _show(self, message: str, seconds: float | None) -> None:
        self.label.config(text=message)
        self.root.update_idletasks()
        w, h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        x = self.root.winfo_screenwidth() - w - 2
        y = self.root.winfo_screenheight() - h - 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.deiconify()
        self.root.lift()
        if sys.platform == "darwin":
            self._place_at_mac_corner()
        self._cancel_timer()
        secs = self.default_seconds if seconds is None else seconds
        if secs > 0:
            self._hide_job = self.root.after(int(secs * 1000), self._hide)

    def _place_at_mac_corner(self) -> None:
        # Native placement reaches the screen edge, including the Dock area.
        import AppKit

        self.root.update_idletasks()
        for window in AppKit.NSApplication.sharedApplication().windows():
            if window.title() == "AnswerWrite Overlay":
                frame = AppKit.NSScreen.screens()[0].frame()
                window.setLevel_(AppKit.NSStatusWindowLevel + 1)
                window.setCollectionBehavior_(
                    AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
                    | AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
                )
                window.setFrameOrigin_(AppKit.NSMakePoint(
                    frame.origin.x + frame.size.width - window.frame().size.width - 2,
                    frame.origin.y + 2,
                ))
                break

    def _hide(self) -> None:
        self._cancel_timer()
        self.root.withdraw()
        self.root.update_idletasks()

    def _cancel_timer(self) -> None:
        if self._hide_job:
            self.root.after_cancel(self._hide_job)
            self._hide_job = None


if sys.platform == "darwin":
    from .mac_popup import MacPopup as Popup
