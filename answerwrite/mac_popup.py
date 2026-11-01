"""A native macOS panel that never becomes the active application."""
import queue
import threading
import time

import AppKit
import Foundation
import objc


class PassivePanel(AppKit.NSPanel):
    def canBecomeKeyWindow(self):
        return False

    def canBecomeMainWindow(self):
        return False


class DismissButton(AppKit.NSButton):
    def acceptsFirstMouse_(self, event):
        return True


class PopupEvents(Foundation.NSObject):
    @objc.IBAction
    def dismiss_(self, sender):
        self.owner._hide()

    def tick_(self, timer):
        self.owner._drain()


class MacPopup:
    def __init__(self, default_seconds):
        self.default_seconds = default_seconds
        self._queue = queue.Queue()
        self._deadline = None
        self.app = AppKit.NSApplication.sharedApplication()
        self.app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyProhibited)
        self.panel = PassivePanel.alloc().initWithContentRect_styleMask_backing_defer_(
            AppKit.NSMakeRect(0, 0, 100, 28),
            AppKit.NSWindowStyleMaskBorderless | AppKit.NSWindowStyleMaskNonactivatingPanel,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        self.panel.setTitle_('AnswerWrite Overlay')
        self.panel.setReleasedWhenClosed_(False)
        self.panel.setHidesOnDeactivate_(False)
        self.panel.setBecomesKeyOnlyIfNeeded_(True)
        self.panel.setLevel_(AppKit.NSStatusWindowLevel + 1)
        self.panel.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        self.panel.setBackgroundColor_(AppKit.NSColor.colorWithCalibratedWhite_alpha_(0.13, 1))
        self.panel.setAlphaValue_(0.45)
        self.panel.setHasShadow_(False)
        self.events = PopupEvents.alloc().init()
        self.events.owner = self
        self.button = DismissButton.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, 100, 28))
        self.button.setBordered_(False)
        self.button.setButtonType_(AppKit.NSButtonTypeMomentaryChange)
        self.button.setTarget_(self.events)
        self.button.setAction_('dismiss:')
        self.button.setFocusRingType_(AppKit.NSFocusRingTypeNone)
        self.panel.contentView().addSubview_(self.button)
        self.timer = Foundation.NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.05, self.events, 'tick:', None, True,
        )

    def show(self, message, seconds=None):
        self._queue.put(('show', message, seconds))

    def hide(self, wait=False):
        done = threading.Event() if wait else None
        self._queue.put(('hide', done, None))
        if done is not None and not done.wait(2):
            raise RuntimeError('The popup did not hide before screen capture.')

    def _drain(self):
        while True:
            try:
                action, value, seconds = self._queue.get_nowait()
            except queue.Empty:
                break
            if action == 'show':
                self._show(value, seconds)
            else:
                self._hide()
                if value is not None:
                    value.set()
        if self._deadline is not None and time.monotonic() >= self._deadline:
            self._hide()

    def _show(self, message, seconds):
        paragraph = AppKit.NSMutableParagraphStyle.alloc().init()
        paragraph.setAlignment_(AppKit.NSTextAlignmentLeft)
        paragraph.setLineBreakMode_(AppKit.NSLineBreakByWordWrapping)
        attrs = {
            AppKit.NSFontAttributeName: AppKit.NSFont.systemFontOfSize_(13),
            AppKit.NSForegroundColorAttributeName: AppKit.NSColor.whiteColor(),
            AppKit.NSParagraphStyleAttributeName: paragraph,
        }
        title = Foundation.NSAttributedString.alloc().initWithString_attributes_(message, attrs)
        bounds = title.boundingRectWithSize_options_(
            AppKit.NSMakeSize(520, 10000), AppKit.NSStringDrawingUsesLineFragmentOrigin,
        )
        width, height = int(bounds.size.width + 17), int(bounds.size.height + 9)
        self.button.setAttributedTitle_(title)
        self.button.cell().setWraps_(True)
        self.button.cell().setLineBreakMode_(AppKit.NSLineBreakByWordWrapping)
        self.button.setFrame_(AppKit.NSMakeRect(8, 4, width - 16, height - 8))
        screen = AppKit.NSScreen.screens()[0].frame()
        self.panel.setFrame_display_(AppKit.NSMakeRect(
            screen.origin.x + screen.size.width - width - 2,
            screen.origin.y + 2, width, height,
        ), True)
        # This orders the panel without making it key or activating Python.
        self.panel.orderFrontRegardless()
        duration = self.default_seconds if seconds is None else seconds
        self._deadline = time.monotonic() + duration if duration > 0 else None

    def _hide(self):
        self._deadline = None
        self.panel.orderOut_(None)

    def run(self):
        self.app.run()

    def quit(self):
        self.app.stop_(None)
        # Wake AppKit's event wait so run() can return after a terminal signal.
        event = AppKit.NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
            AppKit.NSEventTypeApplicationDefined, AppKit.NSMakePoint(0, 0),
            0, 0, 0, None, 0, 0, 0,
        )
        self.app.postEvent_atStart_(event, True)

    def close(self):
        self.timer.invalidate()
        self.panel.close()
        self.events.owner = None
