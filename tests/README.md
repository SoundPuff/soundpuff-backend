# Test Suite Documentation

This directory contains comprehensive unit tests for all API endpoints in the SoundPuff backend.

## Recent updates

- **2025-12-14:** Added `test_songs.py` which covers song/user/playlist search and combined search endpoints.
- Local test status at time of update: **99 passed** (see "Run all tests" commands below).

## Test Files

- **test_auth.py** - Tests for authentication endpoints (signup, login, password reset)
- **test_users.py** - Tests for user management endpoints (profile, follow/unfollow, etc.)
- **test_songs.py** - Tests for search endpoints (songs, users, playlists, combined search)
- **test_playlists.py** - Original playlist tests (basic song addition tests)
- **test_playlists_comprehensive.py** - Comprehensive playlist tests (CRUD, likes, comments, feed)

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Run specific test file
```bash
pytest tests/test_auth.py
pytest tests/test_users.py
pytest tests/test_songs.py
pytest tests/test_playlists_comprehensive.py
```

> Tip: this project often uses the `uv` runner wrapper in scripts; if you use it locally, run:

```bash
uv run pytest -q tests/
```

### Run specific test
```bash
pytest tests/test_auth.py::test_signup_success
pytest tests/test_users.py::test_follow_user_success
```

### Run with verbose output
```bash
pytest tests/ -v
```

### Run with coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

## Test Structure

All tests use **mocking** to avoid dependencies on:
- Real Supabase connections
- Real database connections (except playlist tests which use in-memory SQLite)
- External services

### Fixtures

- `mock_db_session` - Mocked database session
- `mock_supabase` - Mocked Supabase client
- `mock_user` - Mock authenticated user
- `mock_other_user` - Mock second user for testing interactions

### Helper Functions (in conftest.py)

- `cleanup_supabase_user(user_id)` - Cleanup Supabase user after integration tests
- `generate_unique_email()` - Generate unique test email
- `generate_unique_username()` - Generate unique test username

## Supabase User Cleanup

### Unit Tests (Mocked)
Most tests use mocks and don't create real Supabase users, so no cleanup is needed.

### Integration Tests
For integration tests that create real Supabase users:

1. **Database cleanup** - Automatically handled by test teardown
2. **Supabase Auth cleanup** - Requires `SUPABASE_SERVICE_ROLE_KEY`

```python
# Example usage in integration test
try:
    # Create user via API
    response = client.post("/api/v1/auth/signup", json={...})
    user_id = extract_user_id_from_token(response.json()["access_token"])
finally:
    # Cleanup
    cleanup_supabase_user(user_id)
```

### Manual Cleanup
If tests fail and users aren't cleaned up:

1. Check the database:
```sql
SELECT id, username FROM users WHERE username LIKE 'testuser_%';
```

2. Delete test users:
```sql
DELETE FROM users WHERE username LIKE 'testuser_%';
```

3. For Supabase Auth, use the Supabase dashboard:
   - Go to Authentication > Users
   - Search for test emails (test_*@example.com)
   - Delete manually or use admin API

## Test Coverage

### Authentication (test_auth.py)
- ✅ Signup success
- ✅ Signup with duplicate username
- ✅ Signup with Supabase failure
- ✅ Login success
- ✅ Login with invalid credentials
- ✅ Login with Supabase exception
- ✅ Password reset request
- ✅ Password reset request with exception
- ✅ Password reset confirm success
- ✅ Password reset confirm with invalid token
- ✅ Password reset confirm with exception
- ✅ Integration test with cleanup (optional)

### Users (test_users.py)
- ✅ Read current user profile
- ✅ Update user bio
- ✅ Update user avatar
- ✅ Update both bio and avatar
- ✅ Read user by username
- ✅ Read non-existent user
- ✅ Follow user success
- ✅ Follow non-existent user
- ✅ Attempt to follow self
- ✅ Follow when already following
- ✅ Unfollow user success
- ✅ Unfollow non-existent user
- ✅ Unfollow when not following
- ✅ Get user followers
- ✅ Get followers of non-existent user
- ✅ Get user following list
- ✅ Get following of non-existent user
- ✅ Get empty followers list

### Songs/Search (test_songs.py)
- ✅ Search songs by title
- ✅ Search songs by artist
- ✅ Search songs with pagination
- ✅ Search songs with no results
- ✅ Search songs requires authentication
- ✅ Search users by username
- ✅ Search users by bio
- ✅ Search users with pagination
- ✅ Search users with no results
- ✅ Search playlists by title
- ✅ Search playlists by description
- ✅ Search includes user's private playlists
- ✅ Search playlists with no results
- ✅ Combined search all types
- ✅ Combined search filter by users
- ✅ Combined search filter by songs
- ✅ Combined search filter by playlists
- ✅ Combined search with custom limit
- ✅ Combined search with no results

### Playlists (test_playlists_comprehensive.py)
- ✅ Create public playlist
- ✅ Create private playlist
- ✅ Read public playlists without auth
- ✅ Read playlist by ID
- ✅ Read non-existent playlist
- ✅ Read private playlist unauthorized
- ✅ Update playlist
- ✅ Update playlist as non-owner
- ✅ Delete playlist
- ✅ Delete playlist as non-owner
- ✅ Add song to playlist success
- ✅ Add duplicate song to playlist
- ✅ Add song as non-owner
- ✅ Add non-existent song
- ✅ Add song to non-existent playlist
- ✅ Like playlist
- ✅ Like already liked playlist
- ✅ Unlike playlist
- ✅ Unlike not-liked playlist
- ✅ Create comment
- ✅ Read playlist comments
- ✅ Update comment
- ✅ Update comment as non-owner
- ✅ Delete comment
- ✅ Delete comment as non-owner
- ✅ Read empty feed

## Notes

1. **Mocking Strategy**: Tests use mocks to isolate functionality and avoid external dependencies
2. **Cleanup**: Most tests clear `app.dependency_overrides` after execution
3. **Database**: Playlist tests use in-memory SQLite for speed and isolation
4. **Supabase**: Auth tests mock Supabase client to avoid real API calls
5. **Test Data**: Unique identifiers (UUID) ensure test isolation

## Environment Variables

For integration tests (optional):
```bash
export SUPABASE_URL="your-supabase-url"
export SUPABASE_ANON_KEY="your-anon-key"
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"  # For cleanup
export DATABASE_URL="your-database-url"
```

For unit tests (mocked), only basic config is needed (set in conftest.py):
```bash
export SECRET_KEY="test-secret-key"
```

## Contributing

When adding new endpoints:
1. Create corresponding test file or add to existing file
2. Mock external dependencies (database, Supabase)
3. Test both success and failure cases
4. Test authorization/permission checks
5. Add cleanup in test teardown
6. Update this README with new test coverage
