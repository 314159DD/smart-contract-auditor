"""Supabase client singleton."""
from __future__ import annotations

from supabase import create_client, Client

from src.config import settings

_client: Client | None = None
_admin_client: Client | None = None


def get_db() -> Client:
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


def get_admin_db() -> Client:
    """Admin client using service role key — bypasses RLS, used for user creation."""
    global _admin_client
    if _admin_client is None:
        if not settings.supabase_url or not settings.supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
        _admin_client = create_client(settings.supabase_url, settings.supabase_key)
    return _admin_client
