import base64
import io
import unittest
from unittest.mock import patch, Mock
from PIL import Image
from pynput import keyboard
from answerwrite.hotkeys import GlobalHotkey, parse_hotkey
from answerwrite.capture import to_jpeg_b64, _mac_monitor_bbox
from answerwrite.providers import ClaudeProvider, format_answer


class Tests(unittest.TestCase):
    def test_option_comma_physical_key(self):
        callback = Mock()
        shortcut = GlobalHotkey('alt+comma', callback)
        shortcut._press(keyboard.Key.alt_l)
        shortcut._press(keyboard.KeyCode.from_char('≤', vk=43))
        shortcut._press(keyboard.KeyCode.from_char('≤', vk=43))
        callback.assert_called_once()
        shortcut._release(keyboard.KeyCode.from_char(',', vk=43))
        shortcut._press(keyboard.KeyCode.from_char('≤', vk=43))
        self.assertEqual(callback.call_count, 2)

    def test_bad_shortcut(self):
        for shortcut in ('bogus+comma', 'alt+alt', 'a'):
            with self.assertRaises(ValueError):
                parse_hotkey(shortcut)

    def test_resize(self):
        encoded = to_jpeg_b64(Image.new('RGBA', (3000, 2000)), 1280)
        image = Image.open(io.BytesIO(base64.b64decode(encoded)))
        self.assertEqual(image.size, (1280, 853))
        self.assertEqual(image.mode, 'RGB')

    def test_answers(self):
        self.assertEqual(format_answer('1. B\n2. 56'), '1. B\n2. 56')
        self.assertEqual(format_answer('2.5'), '2.5')

    def test_claude_request(self):
        with patch('anthropic.Anthropic') as client:
            client.return_value.messages.create.return_value = Mock(
                stop_reason='end_turn', content=[Mock(type='text', text='1. B')])
            provider = ClaudeProvider('test-model', 'high')
            self.assertEqual(provider.answer('test-image'), 'B')
            args = client.return_value.messages.create.call_args.kwargs
            self.assertEqual(args['messages'][0]['content'][0]['source']['data'], 'test-image')
            self.assertNotIn('fallbacks', args)

    def test_left_display(self):
        from types import SimpleNamespace as S
        import Quartz
        bounds = {1:S(origin=S(x=0,y=0),size=S(width=1440,height=900)),
                  2:S(origin=S(x=-1920,y=-200),size=S(width=1920,height=1080))}
        with patch.object(Quartz,'CGEventGetLocation',return_value=S(x=-100,y=100)), \
             patch.object(Quartz,'CGGetActiveDisplayList',return_value=(0,[1,2],2)), \
             patch.object(Quartz,'CGMainDisplayID',return_value=1), \
             patch.object(Quartz,'CGDisplayBounds',side_effect=bounds.get):
            self.assertEqual(_mac_monitor_bbox(), (-1920,-200,1920,1080))

if __name__ == '__main__':
    unittest.main()
