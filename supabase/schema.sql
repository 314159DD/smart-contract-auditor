-- Supabase schema for Contract Auditor
-- Run this in the Supabase SQL editor to initialize the database.

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Profiles table (extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email           TEXT,
    tier            TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'pro', 'enterprise')),
    monthly_scan_count   INTEGER NOT NULL DEFAULT 0,
    billing_period_start TIMESTAMPTZ DEFAULT now(),
    stripe_customer_id   TEXT,
    stripe_subscription_id TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Audits table
CREATE TABLE IF NOT EXISTS public.audits (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending','scanning','analyzing','complete','failed')),
    scan_type       TEXT NOT NULL DEFAULT 'quick'
                      CHECK (scan_type IN ('quick','standard','deep')),
    contract_name   TEXT,
    contract_address TEXT,
    chain           TEXT,
    risk_score      FLOAT,
    verdict         TEXT,
    result_json     JSONB,
    ai_cost_usd     FLOAT DEFAULT 0,
    scan_duration_seconds FLOAT DEFAULT 0,
    error           TEXT,
    -- Sharing
    share_slug      TEXT UNIQUE,
    sharing_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    -- Timestamps
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

-- Payment failures table (for failed invoice tracking)
CREATE TABLE IF NOT EXISTS public.payment_failures (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stripe_customer_id   TEXT NOT NULL,
    invoice_id           TEXT,
    amount_due           INTEGER,
    created_at           TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_audits_user_id    ON public.audits(user_id);
CREATE INDEX IF NOT EXISTS idx_audits_status     ON public.audits(status);
CREATE INDEX IF NOT EXISTS idx_audits_share_slug ON public.audits(share_slug) WHERE share_slug IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_profiles_stripe   ON public.profiles(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;

-- Row Level Security
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audits ENABLE ROW LEVEL SECURITY;

-- Profiles: user can read/update their own profile
CREATE POLICY "profiles_select_own" ON public.profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "profiles_update_own" ON public.profiles
    FOR UPDATE USING (auth.uid() = id);

-- Audits: owner can do everything; public can read shared audits
CREATE POLICY "audits_select_own" ON public.audits
    FOR SELECT USING (
        auth.uid() = user_id
        OR (sharing_enabled = TRUE AND share_slug IS NOT NULL)
        OR user_id IS NULL  -- anonymous audits
    );

CREATE POLICY "audits_insert_own" ON public.audits
    FOR INSERT WITH CHECK (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "audits_update_own" ON public.audits
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "audits_delete_own" ON public.audits
    FOR DELETE USING (auth.uid() = user_id);

-- Service role can bypass RLS (for backend operations)
-- This is automatic for service_role key in Supabase

-- Function: increment scan count and reset monthly if needed
CREATE OR REPLACE FUNCTION public.increment_scan_count(user_id UUID)
RETURNS void AS $$
DECLARE
    period_start TIMESTAMPTZ;
BEGIN
    SELECT billing_period_start INTO period_start
    FROM public.profiles WHERE id = user_id;

    -- Reset count if new billing month
    IF period_start IS NULL OR date_trunc('month', now()) > date_trunc('month', period_start) THEN
        UPDATE public.profiles
        SET monthly_scan_count = 1, billing_period_start = now(), updated_at = now()
        WHERE id = user_id;
    ELSE
        UPDATE public.profiles
        SET monthly_scan_count = monthly_scan_count + 1, updated_at = now()
        WHERE id = user_id;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger: auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.profiles (id, email)
    VALUES (new.id, new.email)
    ON CONFLICT (id) DO NOTHING;
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
