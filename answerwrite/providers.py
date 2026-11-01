import json
import re
import urllib.error
import urllib.request
from typing import Protocol

from .config import Config

SYSTEM_PROMPT = (
    "You answer questions from a screenshot. "
    "Find EVERY question visible on screen and output one line per question, "
    "in top-to-bottom order, formatted '<question number>. <answer>'.\n"
    "- Multiple-choice question: the answer is the letter of the correct choice.\n"
    "- Question with a numeric answer (math, counts, fill in the number): the answer is "
    "just the number, e.g. 56, -3, 2.5, 3/4 or 40%.\n"
    "Example:\n1. B\n2. 56\n3. A\n"
    "Use the question numbers shown on screen if there are any, otherwise number them 1, 2, 3. "
    "Output only those lines: no explanation, no working, no choice text. "
    "If unsure, give your best answer. If there is no question on screen, output '?'."
)
USER_PROMPT = "Answer every question in this screenshot."
MAX_OUTPUT_TOKENS = 200

# A choice letter, or a number like 56, -3, 1,200, 2.5, 3/4, 40%
_ANSWER = r"(?:[A-H](?![A-Za-z])|-?\d[\d,]*(?:\.\d+)?(?:/\d+)?%?)"
_NUMBERED_LINE = re.compile(
    # "1. B", "Q7) 56"; a space is required after "." so "2.5" isn't read as "2. 5"
    rf"^\W*?(?:Q(?:uestion)?\s*)?(\d+)\s*(?:\)\s*|[.:\-]\s+)\(?({_ANSWER})",
    re.IGNORECASE | re.MULTILINE,
)
_BARE_ANSWER_LINE = re.compile(rf"^\s*\(?({_ANSWER})\)?\.?\s*$", re.IGNORECASE | re.MULTILINE)

_LETTER_PATTERNS = [
    re.compile(r"^\W*([A-H])\b"),  # "B", "B)", "(B) Paris"
    re.compile(r"answer\W+(?:is\W+)?\(?([A-H])\b", re.IGNORECASE),  # "The answer is B"
    re.compile(r"\b([A-H])\)"),  # "... C) Paris"
]


def _clean(answer: str) -> str:
    return answer.upper() if answer[0].isalpha() else answer


def extract_letter(text: str) -> str:
    """Reduce a model reply to a single answer (choice letter or number), if one can be found."""
    bare = _BARE_ANSWER_LINE.fullmatch(text.strip())
    if bare:
        return _clean(bare.group(1))
    for pattern in _LETTER_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1).upper()
    return text.strip() or "?"


def format_answer(text: str) -> str:
    """'1. B\\n2. 56' for several questions, or just the answer for one."""
    numbered = _NUMBERED_LINE.findall(text)
    if len(numbered) >= 2:
        return "\n".join(f"{num}. {_clean(ans)}" for num, ans in numbered)
    if len(numbered) == 1:
        return _clean(numbered[0][1])
    bare = _BARE_ANSWER_LINE.findall(text)
    if len(bare) >= 2:
        return "\n".join(f"{i}. {_clean(ans)}" for i, ans in enumerate(bare, 1))
    return extract_letter(text)


class Provider(Protocol):
    def answer(self, image_b64: str) -> str: ...


class OllamaProvider:
    def __init__(self, host: str, model: str):
        self.host = host
        self.model = model

    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            f"{self.host}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            raise RuntimeError(f"Ollama error {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cannot reach Ollama at {self.host} - is it running?") from exc

    def answer(self, image_b64: str) -> str:
        data = self._post(
            "/api/chat",
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_PROMPT, "images": [image_b64]},
                ],
                "stream": False,
                "think": False,
                "keep_alive": "30m",
                "options": {"num_predict": MAX_OUTPUT_TOKENS, "temperature": 0},
            },
        )
        text = data.get("message", {}).get("content", "")
        # Reasoning models may still emit <think> blocks; drop them
        return format_answer(re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL))

    def warm_up(self) -> None:
        """Load the model into memory so the first hotkey press is fast."""
        self._post("/api/generate", {"model": self.model, "keep_alive": "30m"})


class ClaudeProvider:
    # Claude thinks before answering (it can't be turned off on current models), so the
    # cap has to cover the thinking too; the visible reply is still just the answer lines.
    MAX_TOKENS = 16000

    def __init__(self, model: str, effort: str, workspace_id: str | None = None):
        import anthropic

        # User-level keys (sk-ant-usr-...) aren't tied to a workspace, so name one per request
        headers = {"anthropic-workspace-id": workspace_id} if workspace_id else None
        self.client = anthropic.Anthropic(default_headers=headers)  # reads ANTHROPIC_API_KEY
        self.model = model
        self.effort = effort

    def answer(self, image_b64: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.MAX_TOKENS,
            output_config={"effort": self.effort},
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64},
                        },
                        {"type": "text", "text": USER_PROMPT},
                    ],
                }
            ],
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("Claude declined to answer this one.")
        if response.stop_reason == "max_tokens":
            raise RuntimeError("Claude ran out of tokens before answering; try a lower CLAUDE_EFFORT.")
        return format_answer("".join(b.text for b in response.content if b.type == "text"))


def make_provider(cfg: Config) -> Provider:
    if cfg.provider == "claude":
        return ClaudeProvider(cfg.claude_model, cfg.claude_effort, cfg.anthropic_workspace_id)
    return OllamaProvider(cfg.ollama_host, cfg.ollama_model)
