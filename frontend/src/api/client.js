// Auth tokens live in httpOnly cookies that JavaScript can't read; the browser sends them automatically.
const UNSAFE_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE'];
const NO_REFRESH_PATHS = ['/api/auth/login', '/api/auth/register', '/api/auth/refresh', '/api/auth/logout'];

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

function getCookie(name) {
  return document.cookie
    .split('; ')
    .find((c) => c.startsWith(`${name}=`))
    ?.slice(name.length + 1);
}

async function request(path, { method = 'GET', body } = {}) {
  const headers = {};
  if (body) headers['Content-Type'] = 'application/json';
  const csrf = getCookie('csrf_token');
  if (csrf && UNSAFE_METHODS.includes(method)) headers['X-CSRF-Token'] = csrf;

  const res = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    credentials: 'include',
  });
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  return { res, data };
}

// Share one refresh call between requests that hit a 401 at the same time.
let refreshing = null;

function refreshSession() {
  refreshing ??= request('/api/auth/refresh', { method: 'POST' })
    .then(({ res }) => res.ok)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

export async function api(path, options) {
  let { res, data } = await request(path, options);

  // Access token (15 min) expired: get a new one with the refresh token cookie, then retry once.
  if (res.status === 401 && !NO_REFRESH_PATHS.includes(path) && (await refreshSession())) {
    ({ res, data } = await request(path, options));
  }

  if (!res.ok) throw new ApiError(errorMessage(data), res.status);
  return data;
}
