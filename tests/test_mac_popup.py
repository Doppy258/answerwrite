import sys
import unittest


@unittest.skipUnless(sys.platform == 'darwin', 'Native Mac panel')
class MacPopupTests(unittest.TestCase):
    def test_popup_preserves_focus(self):
        import AppKit
        import Foundation
        from answerwrite.mac_popup import MacPopup
        workspace = AppKit.NSWorkspace.sharedWorkspace()
        active_pid = workspace.frontmostApplication().processIdentifier()
        popup = MacPopup(0.1)
        try:
            for message in ('Ready', 'Thinking...', '1. B\n2. 56'):
                popup._show(message, 0.1)
                self.assertTrue(popup.panel.isVisible())
                self.assertFalse(popup.panel.canBecomeKeyWindow())
                self.assertFalse(popup.panel.canBecomeMainWindow())
                Foundation.NSRunLoop.currentRunLoop().runUntilDate_(
                    Foundation.NSDate.dateWithTimeIntervalSinceNow_(0.2))
                self.assertEqual(workspace.frontmostApplication().processIdentifier(), active_pid)
                self.assertFalse(popup.panel.isVisible())
            popup._show('Dismiss', 0)
            popup.events.dismiss_(None)
            self.assertFalse(popup.panel.isVisible())
        finally:
            popup.close()
