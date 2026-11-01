"""Global shortcuts. Mac key codes keep Option+, working on US layouts."""
import sys
from pynput import keyboard

# Physical ANSI keys: Option changes the character, but not the key code.
_MAC_CODES = {
    "a":0,"s":1,"d":2,"f":3,"h":4,"g":5,"z":6,"x":7,"c":8,"v":9,"b":11,
    "q":12,"w":13,"e":14,"r":15,"y":16,"t":17,"1":18,"2":19,"3":20,
    "4":21,"6":22,"5":23,"=":24,"9":25,"7":26,"-":27,"8":28,"0":29,
    "]":30,"o":31,"u":32,"[":33,"i":34,"p":35,"l":37,"j":38,"'":39,
    "k":40,";":41,",":43,"/":44,"n":45,"m":46,".":47," ":49,
}
_MODS = {"alt":"alt", "option":"alt", "ctrl":"ctrl", "control":"ctrl", "shift":"shift", "cmd":"cmd", "command":"cmd", "super":"cmd"}


def parse_hotkey(value: str):
    parts = value.lower().replace("+ ", "+").split("+")
    keys = []
    for part in parts:
        part = part.strip().strip("<>")
        part = {"comma":",", "space":" "}.get(part, part)
        if part in _MODS:
            keys.append(getattr(keyboard.Key, _MODS[part]))
        elif sys.platform == "darwin" and part in _MAC_CODES:
            keys.append(keyboard.KeyCode.from_vk(_MAC_CODES[part]))
        elif len(part) == 1:
            keys.append(keyboard.KeyCode.from_char(part))
        else:
            try:
                key = getattr(keyboard.Key, part)
                keys.append(keyboard.KeyCode.from_vk(key.value.vk) if sys.platform == "darwin" else key)
            except AttributeError as exc:
                raise ValueError(f"Unknown shortcut key: {part!r}") from exc
    if len(keys) < 2 or len(set(keys)) != len(keys):
        raise ValueError("HOTKEY needs a modifier and a key, for example alt+comma.")
    return keys


class GlobalHotkey:
    def __init__(self, shortcut, callback):
        self.hotkey = keyboard.HotKey(parse_hotkey(shortcut), callback)
        self.listener = keyboard.Listener(on_press=self._press, on_release=self._release)

    def _canonical(self, key):
        if sys.platform == "darwin" and isinstance(key, keyboard.KeyCode) and key.vk is not None:
            return keyboard.KeyCode.from_vk(key.vk)
        return self.listener.canonical(key)

    def _press(self, key):
        self.hotkey.press(self._canonical(key))

    def _release(self, key):
        self.hotkey.release(self._canonical(key))

    def start(self):
        self.listener.start()
        self.listener.wait()

    def stop(self):
        self.listener.stop()
