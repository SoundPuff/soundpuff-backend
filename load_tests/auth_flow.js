import http from 'k6/http';
import { check, sleep } from 'k6';
import { BASE_URL, options as baseOptions } from './config.js';

export const options = {
  ...baseOptions,
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m', target: 10 },
    { duration: '30s', target: 0 },
  ],
};

const EMAIL = __ENV.TEST_EMAIL || 'test@test.com';
const PASSWORD = __ENV.TEST_PASSWORD || 'testuser';

export default function () {
  const payload = JSON.stringify({
    email: EMAIL,
    password: PASSWORD,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const loginRes = http.post(`${BASE_URL}/auth/login`, payload, params);
  
  const loginSuccessful = check(loginRes, {
    'login status is 200': (r) => r.status === 200,
    'has access token': (r) => r.json().access_token !== undefined,
  });

  if (loginSuccessful) {
    const authToken = loginRes.json().access_token;
    const authParams = {
      headers: {
        'Authorization': `Bearer ${authToken}`,
      },
    };

    // Test an authenticated endpoint
    const meRes = http.get(`${BASE_URL}/users/me`, authParams);
    check(meRes, {
      'get me status is 200': (r) => r.status === 200,
    });
  }

  sleep(1);
}
