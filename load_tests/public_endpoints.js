import http from 'k6/http';
import { check, sleep } from 'k6';
import { BASE_URL, options as baseOptions } from './config.js';

export const options = {
  ...baseOptions,
  stages: [
    { duration: '30s', target: 20 }, // ramp up to 20 users
    { duration: '1m', target: 20 },  // stay at 20 users
    { duration: '30s', target: 0 },  // ramp down to 0 users
  ],
};

export default function () {
  // 1. Get songs
  const songsRes = http.get(`${BASE_URL}/songs`);
  check(songsRes, {
    'get songs status is 200': (r) => r.status === 200,
    'get songs has data': (r) => r.json().length > 0,
  });

  sleep(1);

  // 2. Get playlists
  const playlistsRes = http.get(`${BASE_URL}/playlists`);
  check(playlistsRes, {
    'get playlists status is 200': (r) => r.status === 200,
  });

  sleep(1);

  // 3. Search
  const searchRes = http.get(`${BASE_URL}/songs/search?q=test`);
  check(searchRes, {
    'search status is 200': (r) => r.status === 200,
  });

  sleep(1);
}
