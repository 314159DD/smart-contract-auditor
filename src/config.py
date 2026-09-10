"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # OpenRouter (AI provider)
    openrouter_api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    ai_model: str = field(default_factory=lambda: os.getenv("AI_MODEL", "anthropic/claude-sonnet-4-6"))

    # Supabase
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_key: str = field(default_factory=lambda: os.getenv("SUPABASE_KEY", ""))

    # Etherscan
    etherscan_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ETHERSCAN_API_KEY"))

    # Stripe
    stripe_secret_key: str = field(default_factory=lambda: os.getenv("STRIPE_SECRET_KEY", ""))
    stripe_webhook_secret: str = field(default_factory=lambda: os.getenv("STRIPE_WEBHOOK_SECRET", ""))

    # Email (Resend)
    resend_api_key: Optional[str] = field(default_factory=lambda: os.getenv("RESEND_API_KEY"))
    email_from: str = field(default_factory=lambda: os.getenv("EMAIL_FROM", "noreply@contractauditor.app"))
    frontend_url: str = field(default_factory=lambda: os.getenv("FRONTEND_URL", "http://localhost:3000"))

    # Alert webhook (optional)
    alert_webhook_url: Optional[str] = field(default_factory=lambda: os.getenv("ALERT_WEBHOOK_URL"))

    # App settings
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", "change-me-in-production"))

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def validate(self) -> list[str]:
        """Return list of missing required config keys."""
        errors = []
        if not self.openrouter_api_key:
            errors.append("OPENROUTER_API_KEY is required")
        return errors


# Singleton instance
settings = Config()
