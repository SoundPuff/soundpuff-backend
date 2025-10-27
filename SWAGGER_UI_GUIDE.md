# Swagger UI Guide

This guide explains how to use Swagger UI to test your SoundPuff API.

## Accessing Swagger UI

Once your server is running:

```bash
uv run uvicorn app.main:app --reload
```

Visit: **http://localhost:8000/api/v1/docs**

Alternative documentation: **http://localhost:8000/api/v1/redoc** (ReDoc format)

## Features

### 🎨 Enhanced UI Features
- **Persistent Authorization**: Your auth token is saved across page refreshes
- **Request Duration Display**: See how long each request takes
- **Filter**: Search for specific endpoints
- **Try It Out**: Interactive testing of all endpoints

### 📋 Organized by Tags

Endpoints are organized into categories:
- **Authentication**: Sign up and login
- **Users**: User profile management and social features
- **Playlists**: Playlist CRUD operations, likes, and comments

## How to Test Authentication Flow

### Step 1: Sign Up
1. Scroll to **Authentication** section
2. Click on `POST /api/v1/auth/signup`
3. Click **"Try it out"**
4. Fill in the request body:
   ```json
   {
     "email": "test@example.com",
     "password": "SecurePassword123!",
     "username": "testuser"
   }
   ```
5. Click **"Execute"**
6. **Copy the `access_token`** from the response

### Step 2: Authorize
1. Look for the **"Authorize" button** at the top-right (🔓 icon)
2. Click it
3. In the popup, enter your token:
   - **Just paste the token** (without "Bearer" prefix)
   - Swagger UI will automatically add "Bearer" for you
4. Click **"Authorize"**
5. Click **"Close"**

You're now authenticated! 🎉 The lock icon should change to 🔒

### Step 3: Test Protected Endpoints
1. Try any protected endpoint (e.g., `GET /api/v1/users/me`)
2. Click **"Try it out"**
3. Click **"Execute"**
4. You should see your user profile in the response

## Common Use Cases

### Creating a Playlist
1. Make sure you're authenticated (see above)
2. Go to **Playlists** → `POST /api/v1/playlists/`
3. Click "Try it out"
4. Enter:
   ```json
   {
     "title": "My Awesome Playlist",
     "description": "Collection of my favorite songs"
   }
   ```
5. Execute

### Following a User
1. Get another user's username (create another account or use existing)
2. Go to **Users** → `POST /api/v1/users/{username}/follow`
3. Enter the username in the path parameter
4. Execute

### Viewing Your Feed
1. Go to **Playlists** → `GET /api/v1/playlists/feed`
2. This shows playlists from users you follow

## Understanding the Response Codes

- **200 OK**: Request succeeded
- **201 Created**: Resource created successfully (signup, create playlist)
- **400 Bad Request**: Invalid input (username taken, validation error)
- **401 Unauthorized**: Not authenticated or invalid token
- **404 Not Found**: Resource doesn't exist
- **422 Unprocessable Entity**: Validation error in request body

## Tips and Tricks

### 🔄 Persistent Authorization
Your token is saved in the browser. You don't need to re-authorize after refreshing the page!

### 🔍 Filter Endpoints
Use the search box to quickly find endpoints:
- Type "playlist" to see all playlist endpoints
- Type "follow" to see follow-related endpoints

### ⏱️ Request Duration
Each response shows how long it took. Useful for performance testing!

### 📝 Examples in Descriptions
Most endpoints have example responses in their descriptions. Check them out!

### 🔄 Testing Multiple Users
To test social features:
1. Open Swagger UI in a **private/incognito window**
2. Sign up a different user
3. Use both windows to test follow/like interactions

## Troubleshooting

### "Not authenticated" error
- Make sure you clicked **Authorize** and entered your token
- Try logging in again to get a fresh token
- Tokens expire after some time (check Supabase settings)

### "User profile not found" error
- This means the user exists in Supabase Auth but not in your database
- Delete the user from Supabase Dashboard and sign up again

### Token format error
- Don't include "Bearer" when pasting in the Authorize popup
- Just paste the raw token: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

### 422 Validation Error
- Check the response body for details on which field is invalid
- Make sure all required fields are filled
- Check data types (strings vs numbers)

## Advanced Features

### Schema Viewer
Click on any endpoint's **"Schema"** tab to see the exact structure of request/response bodies.

### Example Values
Swagger UI auto-generates example values based on your Pydantic schemas. You can click "Example Value" to auto-fill forms!

### Response Samples
Check the **Responses** section under each endpoint to see what successful and error responses look like.

### cURL Commands
After executing a request, scroll down to see the equivalent cURL command. Great for testing outside Swagger!

## Next Steps

- Check out **ReDoc** at http://localhost:8000/api/v1/redoc for a cleaner, read-only view
- See `SUPABASE_AUTH_TESTING.md` for curl and Python examples
- Use the API to build your frontend!

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Supabase Auth Guide](https://supabase.com/docs/guides/auth)
