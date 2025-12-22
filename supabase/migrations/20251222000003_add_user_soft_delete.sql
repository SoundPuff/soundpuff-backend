-- Add soft-delete fields to user profiles
-- Keeps stable user IDs while allowing anonymization + hiding profiles.

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;

-- Optional index for faster filtering of active profiles
CREATE INDEX IF NOT EXISTS idx_users_is_deleted ON public.users(is_deleted);
