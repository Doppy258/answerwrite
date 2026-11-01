import os
import re
import math
from pathlib import Path
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    provider: str
    hotkey: str
    popup_seconds: float
    max_image_edge: int
    ollama_host: str
    ollama_model: str
    claude_model: str
    claude_effort: str
    anthropic_workspace_id: str | None

    @property
    def model(self) -> str:
        return self.claude_model if self.provider == "claude" else self.ollama_model


def load_config() -> Config:
    # .env wins over inherited env vars (e.g. Claude Code sets its own CLAUDE_EFFORT)
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
    provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    if provider not in ("ollama", "claude"):
        raise SystemExit(f"Unknown LLM_PROVIDER {provider!r}; use 'ollama' or 'claude'.")
    cfg = Config(
        provider=provider,
        # The keyboard lib treats "," as a sequence separator, so spell the key out
        hotkey=re.sub(r"\+\s*,", "+comma", os.getenv("HOTKEY", "alt+comma")),
        popup_seconds=float(os.getenv("POPUP_SECONDS", "8")),
        max_image_edge=int(os.getenv("MAX_IMAGE_EDGE", "1280")),
        # "localhost" tries IPv6 first on Windows and stalls ~2s per request
        ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        .rstrip("/")
        .replace("//localhost", "//127.0.0.1"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen3.5:4b"),
        claude_model=os.getenv("CLAUDE_MODEL", "claude-opus-5-5"),
        # low | medium | high | xhigh | max — higher thinks longer (slower, more accurate)
        claude_effort=os.getenv("CLAUDE_EFFORT", "high").strip().lower(),
        # Only needed for user-level keys (sk-ant-usr-...); workspace keys don't need it
        anthropic_workspace_id=os.getenv("ANTHROPIC_WORKSPACE_ID", "").strip() or None,
    )

    if not math.isfinite(cfg.popup_seconds) or cfg.popup_seconds < 0:
        raise SystemExit("POPUP_SECONDS must be zero or a positive number.")
    if cfg.max_image_edge < 64:
        raise SystemExit("MAX_IMAGE_EDGE must be at least 64.")
    if cfg.provider == "claude" and not os.getenv("ANTHROPIC_API_KEY", "").strip():
        raise SystemExit("Add your ANTHROPIC_API_KEY to .env before using Claude.")
    return cfg
