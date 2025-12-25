# Load Testing with k6

This directory contains load testing scripts for the SoundPuff API using [k6](https://k6.io/).

## Prerequisites

- [k6](https://k6.io/docs/getting-started/installation/) installed on your machine.

## Running Tests

### 1. Public Endpoints
Tests `GET /songs`, `GET /playlists`, and search functionality.
```bash
k6 run load_tests/public_endpoints.js
```

### 2. Auth Flow
Tests login and authenticated user profile retrieval.
```bash
k6 run -e TEST_EMAIL=your_email@example.com -e TEST_PASSWORD=your_password load_tests/auth_flow.js
```

### 3. Playlist Flow
Tests login, playlist creation, retrieval, and deletion.
```bash
k6 run -e TEST_EMAIL=your_email@example.com -e TEST_PASSWORD=your_password load_tests/playlist_flow.js
```

### 4. Stress Test
A more aggressive test with higher concurrency and spikes.
```bash
k6 run load_tests/stress_test.js
```

## Configuration

You can override the base URL by setting the `BASE_URL` environment variable:
```bash
k6 run -e BASE_URL=https://api.example.com/api/v1 load_tests/public_endpoints.js
```

### Rate Limiting Note

The API has built-in rate limiting (see `app/core/config.py`). If you hit `429 Too Many Requests` during load testing, you may need to:
1. Increase the limits in `app/core/config.py`.
2. Run the tests with fewer virtual users (VUs).
3. Disable the `SimpleRateLimiterMiddleware` in `app/main.py` for the duration of the test.

## Test Scenarios

- **Public Endpoints**: Simulates users browsing songs and playlists.
- **Auth Flow**: Simulates users logging in and checking their profile.

## Thresholds

The tests are configured with the following thresholds:
- HTTP request failure rate < 1%
- 95th percentile response time < 500ms
