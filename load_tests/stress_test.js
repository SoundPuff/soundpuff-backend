import http from 'k6/http';
import { check, sleep } from 'k6';
import { BASE_URL, options as baseOptions } from './config.js';

export const options = {
  ...baseOptions,
  stages: [
    { duration: '1m', target: 50 },  // ramp up to 50 users
    { duration: '3m', target: 50 },  // stay at 50 users
    { duration: '1m', target: 100 }, // spike to 100 users
    { duration: '2m', target: 100 }, // stay at 100 users
    { duration: '1m', target: 0 },   // ramp down to 0 users
  ],
};

export default function () {
  const responses = http.batch([
    ['GET', `${BASE_URL}/songs`],
    ['GET', `${BASE_URL}/playlists`],
    ['GET', `${BASE_URL}/songs/search?q=test`],
  ]);

  check(responses[0], { 'songs status is 200': (r) => r.status === 200 });
  check(responses[1], { 'playlists status is 200': (r) => r.status === 200 });
  check(responses[2], { 'search status is 200': (r) => r.status === 200 });

  sleep(0.5);
}
