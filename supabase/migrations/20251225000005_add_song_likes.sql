-- Create song_likes join table (many-to-many relationship for song likes)
CREATE TABLE IF NOT EXISTS public.song_likes (
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    song_id BIGINT NOT NULL REFERENCES public.songs(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, song_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_song_likes_user_id ON public.song_likes(user_id);
CREATE INDEX IF NOT EXISTS idx_song_likes_song_id ON public.song_likes(song_id);

-- Enable Row Level Security (RLS)
ALTER TABLE public.song_likes ENABLE ROW LEVEL SECURITY;

-- ============================================
-- SONG_LIKES POLICIES
-- ============================================

-- Anyone can view song likes
CREATE POLICY "Song likes are viewable by everyone"
    ON public.song_likes FOR SELECT
    USING (true);

-- Users can like songs
CREATE POLICY "Users can like songs"
    ON public.song_likes FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can unlike songs
CREATE POLICY "Users can unlike songs"
    ON public.song_likes FOR DELETE
    USING (auth.uid() = user_id);
