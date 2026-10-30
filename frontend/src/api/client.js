import { auth } from '../firebase.js';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

export async function api(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  // Firebase ID token (JWT); the SDK refreshes it automatically before it expires.
  const token = await auth.currentUser?.getIdToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(errorMessage(data), res.status);
  return data;
}
