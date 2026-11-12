from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

# Ranked by side-by-side SVG tests on 2026-11-11/12. Free-tier Gemini keys have no Pro quota,
# and Flash models often return 503 "high demand", so each agent gets a fallback chain.
GEMINI_CODER_CHAIN = "gemini-3.5-flash,gemini-3-flash-preview,gemini-2.5-flash"
GEMINI_FAST_CHAIN = "gemini-3-flash-preview,gemini-3.5-flash,gemini-2.5-flash"
# OpenRouter ":free" models (work with $0 credits); nemotron-3.5-super-vl drew the best shading and glow.
FREE_CHAIN = "nvidia/nemotron-3.5-super-vl:free,dots-studio/dots-3-note-preview:free,nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"

class Settings(BaseSettings):
    # "gemini" or "openrouter". Each agent has its own model per provider; a comma-separated
    # list is a fallback chain tried in order when a model is busy, out of quota or retired.
    LLM_PROVIDER: str = "gemini"

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_BRIEF: str = GEMINI_FAST_CHAIN
    GEMINI_MODEL_DIRECTOR: str = GEMINI_FAST_CHAIN
    GEMINI_MODEL_CODER: str = GEMINI_CODER_CHAIN
    GEMINI_MODEL_REVIEWER: str = GEMINI_FAST_CHAIN

    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    MODEL_BRIEF: str = FREE_CHAIN
    MODEL_DIRECTOR: str = FREE_CHAIN
    MODEL_CODER: str = FREE_CHAIN
    MODEL_REVIEWER: str = FREE_CHAIN
    # Gemini Flash spends part of this on hidden thinking, so keep it generous.
    CODER_MAX_TOKENS: int = 48000

    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    MAX_AGENT_RETRIES: int = 2
    # Network blips: up to 6 connection tries, waiting 2, 4, 8, 16, 30s between them.
    CONNECT_RETRIES: int = 6
    # Render -> vision review -> revise loops after the first draft. 0 disables review.
    REVIEW_ROUNDS: int = 1
    # Pixel density of the preview render (1080x1350 at 2 = 2160x2700).
    PREVIEW_SCALE: int = 2
    OUTPUT_DIR: str = "outputs"
    SSL_VERIFY: bool = True
    # Corporate TLS proxies need the system bundle; certifi alone fails here.
    CA_BUNDLE: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"

    def provider(self) -> str:
        return self.LLM_PROVIDER.strip().lower()

    def model_for(self, role: str) -> str:
        """Model (or fallback chain) for an agent role: brief, director, coder, reviewer."""
        prefix = "GEMINI_MODEL_" if self.provider() == "gemini" else "MODEL_"
        return getattr(self, prefix + role.upper())

    def requests_verify(self):
        if not self.SSL_VERIFY:
            return False
        if self.CA_BUNDLE:
            return self.CA_BUNDLE
        system_bundle = Path("/etc/ssl/certs/ca-certificates.crt")
        return str(system_bundle) if system_bundle.exists() else True


settings = Settings()
