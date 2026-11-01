# AnswerWrite for Mac

Press **Option + comma (,)** to capture the display under your mouse.
The app sends that image to your selected model and shows its answer in a popup.
Click the popup to close it. Press **Control + C** in Terminal to quit the app.

## Setup

```bash
git clone https://github.com/Doppy258/answerwrite.git
cd answerwrite
./Setup.command
open -e .env
```

Add your own API key and provider settings to `.env` before running.
The repository includes `.env.example`; private `.env` files are excluded.

## Run

1. Open this folder in Finder.
2. Double-click **Run.command**.
3. If Mac asks for access, open **System Settings → Privacy & Security**.
4. Allow the app that started Python, usually **Terminal**, under **Accessibility** and **Screen & System Audio Recording** (called **Screen Recording** on some versions).
5. If Mac requests **Input Monitoring**, allow Terminal there too.
6. Quit Terminal fully, then open **Run.command** again.
7. Wait for the Ready popup. Open the question, then press **Option + comma**.

If Mac lists Python instead of Terminal, enable the listed Python app.
Permissions granted to Codex do not necessarily apply to Terminal.
Keep the Terminal window open while you use AnswerWrite.
The Mac popup does not take keyboard focus from your active app.
The popup appears at the very bottom right of the primary display, with 45% opacity. Screen capture follows the mouse.
The shortcut uses US keyboard key positions on Mac.

You can also start it from Terminal:

```bash
cd answerwrite
./Run.command
```

## Set up another Mac

Use Python 3.10 or newer with Tk. The Python installer from python.org includes Tk.
If you use Homebrew Python, Setup.command can install the matching Tk package.

1. Copy the app folder. Do not copy `.venv`; it is specific to this Mac.
2. Double-click **Setup.command**. It installs the Python packages.
3. Add your provider settings to `.env`.
4. Double-click **Run.command** and allow the Mac permissions above.

To edit the hidden settings file from this folder:

```bash
open -e .env
```

## Provider settings

When Claude is selected, each shortcut press sends a screenshot to
Anthropic and can use paid API credits. The port tests do not call the paid API.
The account must have access to the model named in `CLAUDE_MODEL`.

```dotenv
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=your-key-here
CLAUDE_MODEL=claude-sonnet-5-5
CLAUDE_EFFORT=high
```

The example model must be available to your account. If the API reports an unknown model, use a
vision model ID available to your account. Keep `.env` private.

For local processing, install and start Ollama separately. Download a vision
model that fits your Mac. Set its exact name in `.env`:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=your-installed-vision-model
```

Ollama is not installed by Setup.command. The local model must support images.

## Other settings

| Setting | Default | Meaning |
| --- | --- | --- |
| `HOTKEY` | `alt+comma` | Option + comma on Mac. Also supports `ctrl+shift+a`. |
| `POPUP_SECONDS` | `8` | Seconds before the popup closes. Use `0` to keep it visible. |
| `MAX_IMAGE_EDGE` | `1280` | Maximum image width or height sent to the model. |
| `ANTHROPIC_WORKSPACE_ID` | empty | Optional workspace header, preserved from the original app. |

Restart the app after you change `.env`.

## If something fails

- **No shortcut response:** check Accessibility and Input Monitoring. Restart Terminal. Do not run with `sudo`.
- **Screen capture error:** check Screen Recording. Quit and restart Terminal.
- **Missing module or Python error:** run Setup.command again.
- **Claude error:** read the error in Terminal. Check the key, model access, workspace, and account credit.
- **Cannot reach Ollama:** start Ollama and check the model name.
- **Popup hidden:** check the primary display and leave full-screen mode. Some full-screen spaces can hide floating windows.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

These tests use fake model responses. They do not check answer accuracy, account
credit, or model access. The Mac port replaces the Windows keyboard hook and
screen capture path, handles Option key characters, and waits for the popup to
hide before capture. Windows capture code remains, but Windows was not retested.
