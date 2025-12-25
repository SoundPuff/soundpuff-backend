import http from 'k6/http';
import { check, sleep } from 'k6';
import { BASE_URL, options as baseOptions } from './config.js';

export const options = {
  ...baseOptions,
  stages: [
    { duration: '30s', target: 15 },
    { duration: '1m', target: 15 },
    { duration: '30s', target: 0 },
  ],
};

const EMAIL = __ENV.TEST_EMAIL || 'test@example.com';
const PASSWORD = __ENV.TEST_PASSWORD || 'password123';

export default function () {
  // 1. Login
  const loginPayload = JSON.stringify({
    email: EMAIL,
    password: PASSWORD,
  });

  const loginRes = http.post(`${BASE_URL}/auth/login`, loginPayload, {
    headers: { 'Content-Type': 'application/json' },
  });

  if (loginRes.status !== 200) {
    console.log(`Login failed: ${loginRes.status}`);
    return;
  }

  const authToken = loginRes.json().access_token;
  const authParams = {
    headers: {
      'Authorization': `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    },
  };

  // 2. Create a playlist
  const playlistPayload = JSON.stringify({
    title: `Test Playlist ${Math.floor(Math.random() * 1000)}`,
    description: 'Load test playlist',
    privacy: 'public',
  });

  const createRes = http.post(`${BASE_URL}/playlists`, playlistPayload, authParams);
  check(createRes, {
    'create playlist status is 201': (r) => r.status === 201,
  });

  if (createRes.status === 201) {
    const playlistId = createRes.json().id;

    // 3. Get the created playlist
    const getRes = http.get(`${BASE_URL}/playlists/${playlistId}`, authParams);
    check(getRes, {
      'get playlist status is 200': (r) => r.status === 200,
    });

    // 4. Delete the playlist (cleanup)
    const deleteRes = http.del(`${BASE_URL}/playlists/${playlistId}`, null, authParams);
    check(deleteRes, {
      'delete playlist status is 204': (r) => r.status === 204 || r.status === 200,
    });
  }

  sleep(1);
}
