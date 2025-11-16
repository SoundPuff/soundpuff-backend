-- Enable Row Level Security (RLS) on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.playlists ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.songs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.playlist_songs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.follows ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.likes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.comments ENABLE ROW LEVEL SECURITY;

-- ============================================
-- USERS (PROFILES) POLICIES
-- ============================================

-- Anyone can view user profiles
CREATE POLICY "Users are viewable by everyone"
    ON public.users FOR SELECT
    USING (true);

-- Users can insert their own profile
CREATE POLICY "Users can insert their own profile"
    ON public.users FOR INSERT
    WITH CHECK (auth.uid() = id);

-- Users can update their own profile
CREATE POLICY "Users can update their own profile"
    ON public.users FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- ============================================
-- PLAYLISTS POLICIES
-- ============================================

-- Anyone can view playlists
CREATE POLICY "Playlists are viewable by everyone"
    ON public.playlists FOR SELECT
    USING (true);

-- Authenticated users can create playlists
CREATE POLICY "Authenticated users can create playlists"
    ON public.playlists FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own playlists
CREATE POLICY "Users can update their own playlists"
    ON public.playlists FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Users can delete their own playlists
CREATE POLICY "Users can delete their own playlists"
    ON public.playlists FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================
-- SONGS POLICIES
-- ============================================

-- Anyone can view songs
CREATE POLICY "Songs are viewable by everyone"
    ON public.songs FOR SELECT
    USING (true);

-- Authenticated users can add songs
CREATE POLICY "Authenticated users can add songs"
    ON public.songs FOR INSERT
    WITH CHECK (auth.uid() IS NOT NULL);

-- ============================================
-- PLAYLIST_SONGS POLICIES
-- ============================================

-- Anyone can view playlist songs
CREATE POLICY "Playlist songs are viewable by everyone"
    ON public.playlist_songs FOR SELECT
    USING (true);

-- Only playlist owners can add songs to their playlists
CREATE POLICY "Playlist owners can add songs"
    ON public.playlist_songs FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.playlists
            WHERE playlists.id = playlist_songs.playlist_id
            AND playlists.user_id = auth.uid()
        )
    );

-- Only playlist owners can remove songs from their playlists
CREATE POLICY "Playlist owners can remove songs"
    ON public.playlist_songs FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.playlists
            WHERE playlists.id = playlist_songs.playlist_id
            AND playlists.user_id = auth.uid()
        )
    );

-- ============================================
-- FOLLOWS POLICIES
-- ============================================

-- Anyone can view follows
CREATE POLICY "Follows are viewable by everyone"
    ON public.follows FOR SELECT
    USING (true);

-- Users can follow others (but not themselves, enforced by CHECK constraint)
CREATE POLICY "Users can follow others"
    ON public.follows FOR INSERT
    WITH CHECK (auth.uid() = follower_id);

-- Users can unfollow others
CREATE POLICY "Users can unfollow others"
    ON public.follows FOR DELETE
    USING (auth.uid() = follower_id);

-- ============================================
-- LIKES POLICIES
-- ============================================

-- Anyone can view likes
CREATE POLICY "Likes are viewable by everyone"
    ON public.likes FOR SELECT
    USING (true);

-- Users can like playlists
CREATE POLICY "Users can like playlists"
    ON public.likes FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can unlike playlists
CREATE POLICY "Users can unlike playlists"
    ON public.likes FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================
-- COMMENTS POLICIES
-- ============================================

-- Anyone can view comments
CREATE POLICY "Comments are viewable by everyone"
    ON public.comments FOR SELECT
    USING (true);

-- Authenticated users can create comments
CREATE POLICY "Authenticated users can create comments"
    ON public.comments FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own comments
CREATE POLICY "Users can update their own comments"
    ON public.comments FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Users can delete their own comments
CREATE POLICY "Users can delete their own comments"
    ON public.comments FOR DELETE
    USING (auth.uid() = user_id);
