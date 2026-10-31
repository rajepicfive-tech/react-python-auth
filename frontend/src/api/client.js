const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const ACCESS_KEY = 'access_token';
const REFRESH_KEY = 'refresh_token';

export const tokenStore = {
  get: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: ({ access_token, refresh_token }) => {
    localStorage.setItem(ACCESS_KEY, access_token);
    localStorage.setItem(REFRESH_KEY, refresh_token);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

// FastAPI returns `detail` as a string or as a list of validation errors.
function errorMessage(body) {
  if (!body?.detail) return 'Something went wrong';
  if (typeof body.detail === 'string') return body.detail;
  return body.detail.map((d) => `${d.loc.at(-1)}: ${d.msg}`).join(', ');
}

async function request(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => null);
  return { res, data };
}

// Share one refresh call between requests that hit a 401 at the same time.
let refreshing = null;

function refreshTokens() {
  refreshing ??= request('/api/auth/refresh', {
    method: 'POST',
    body: { refresh_token: tokenStore.getRefresh() },
  })
    .then(({ res, data }) => {
      if (!res.ok) throw new ApiError(errorMessage(data), res.status);
      tokenStore.set(data);
    })
    .catch((err) => {
      tokenStore.clear();
      throw err;
    })
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

export async function api(path, options) {
  let { res, data } = await request(path, options);

  // The Firebase ID token lasts 1 hour; renew it once and retry.
  if (res.status === 401 && tokenStore.getRefresh() && !path.startsWith('/api/auth/')) {
    await refreshTokens();
    ({ res, data } = await request(path, options));
  }

  if (!res.ok) throw new ApiError(errorMessage(data), res.status);
  return data;
}
