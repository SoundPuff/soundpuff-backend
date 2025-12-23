-- Fix Supabase linter warning: auth_rls_initplan
-- Wrap calls to auth.<function>() in (select ...) so Postgres evaluates once per statement.

-- ============================================
-- USERS (PROFILES) POLICIES
-- ============================================

ALTER POLICY "Users can insert their own profile"
    ON public.users
    WITH CHECK ((SELECT auth.uid()) = id);

ALTER POLICY "Users can update their own profile"
    ON public.users
    USING ((SELECT auth.uid()) = id)
    WITH CHECK ((SELECT auth.uid()) = id);

-- ============================================
-- PLAYLISTS POLICIES
-- ============================================

ALTER POLICY "Authenticated users can create playlists"
    ON public.playlists
    WITH CHECK ((SELECT auth.uid()) = user_id);

ALTER POLICY "Users can update their own playlists"
    ON public.playlists
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

ALTER POLICY "Users can delete their own playlists"
    ON public.playlists
    USING ((SELECT auth.uid()) = user_id);

-- ============================================
-- SONGS POLICIES
-- ============================================

ALTER POLICY "Authenticated users can add songs"
    ON public.songs
    WITH CHECK ((SELECT auth.uid()) IS NOT NULL);

-- ============================================
-- PLAYLIST_SONGS POLICIES
-- ============================================

ALTER POLICY "Playlist owners can add songs"
    ON public.playlist_songs
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.playlists
            WHERE playlists.id = playlist_songs.playlist_id
              AND playlists.user_id = (SELECT auth.uid())
        )
    );

ALTER POLICY "Playlist owners can remove songs"
    ON public.playlist_songs
    USING (
        EXISTS (
            SELECT 1 FROM public.playlists
            WHERE playlists.id = playlist_songs.playlist_id
              AND playlists.user_id = (SELECT auth.uid())
        )
    );

-- ============================================
-- FOLLOWS POLICIES
-- ============================================

ALTER POLICY "Users can follow others"
    ON public.follows
    WITH CHECK ((SELECT auth.uid()) = follower_id);

ALTER POLICY "Users can unfollow others"
    ON public.follows
    USING ((SELECT auth.uid()) = follower_id);

-- ============================================
-- LIKES POLICIES
-- ============================================

ALTER POLICY "Users can like playlists"
    ON public.likes
    WITH CHECK ((SELECT auth.uid()) = user_id);

ALTER POLICY "Users can unlike playlists"
    ON public.likes
    USING ((SELECT auth.uid()) = user_id);

-- ============================================
-- COMMENT_LIKES POLICIES
-- ============================================

ALTER POLICY "Users can like comments"
    ON public.comment_likes
    WITH CHECK ((SELECT auth.uid()) = user_id);

ALTER POLICY "Users can unlike comments"
    ON public.comment_likes
    USING ((SELECT auth.uid()) = user_id);

-- ============================================
-- COMMENTS POLICIES
-- ============================================

ALTER POLICY "Authenticated users can create comments"
    ON public.comments
    WITH CHECK ((SELECT auth.uid()) = user_id);

ALTER POLICY "Users can update their own comments"
    ON public.comments
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

ALTER POLICY "Users can delete their own comments"
    ON public.comments
    USING ((SELECT auth.uid()) = user_id);
