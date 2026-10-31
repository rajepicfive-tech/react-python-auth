import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client.js';
import { useAuth } from '../context/AuthContext.jsx';

const formatTime = (iso) => new Date(iso).toLocaleTimeString();
const formatDateTime = (iso) => new Date(iso).toLocaleString();

function formatDuration(seconds) {
  if (seconds <= 0) return 'expired';
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (d) return `${d}d ${h}h ${m}m`;
  if (h) return `${h}h ${m}m ${s}s`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function describeDevice(ua = '') {
  const browser = ['Edg', 'OPR', 'Chrome', 'Firefox', 'Safari', 'curl', 'python'].find((b) => ua.includes(b)) || 'Unknown';
  const os = ['iPhone', 'iPad', 'Android', 'Mac OS', 'Windows', 'Linux'].find((o) => ua.includes(o)) || '';
  const names = { Edg: 'Edge', OPR: 'Opera' };
  return `${names[browser] || browser}${os ? ` on ${os.replace('Mac OS', 'macOS')}` : ''}`;
}

export default function Session() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [info, setInfo] = useState(null);
  const [fetchedAt, setFetchedAt] = useState(0);
  const [accessDropped, setAccessDropped] = useState(false);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [, setTick] = useState(0);

  const load = useCallback(async () => {
    const data = await api('/api/auth/session');
    setInfo(data);
    setFetchedAt(Date.now());
    setAccessDropped(false);
    return data;
  }, []);

  useEffect(() => {
    load().catch((err) => setMessage(err.message));
    const timer = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(timer);
  }, [load]);

  const remaining = (token) => (token ? Math.max(0, token.expires_in - Math.floor((Date.now() - fetchedAt) / 1000)) : 0);

  const run = async (action) => {
    setBusy(true);
    setMessage('');
    try {
      await action();
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setBusy(false);
    }
  };

  const expireAccess = () =>
    run(async () => {
      await api('/api/auth/expire-access', { method: 'POST' });
      setAccessDropped(true);
      setMessage('Access token removed from the browser. Click "Call protected API" to watch the automatic refresh.');
    });

  const callProtectedApi = () =>
    run(async () => {
      const before = info?.refresh_token?.jti;
      await api('/api/dashboard');
      const after = (await load()).refresh_token?.jti;
      setMessage(
        before !== after
          ? 'GET /api/dashboard → 200. The access token had expired, so the app called /api/auth/refresh, got new tokens and retried.'
          : 'GET /api/dashboard → 200. The access token was still valid, so no refresh was needed.'
      );
    });

  const refreshNow = () =>
    run(async () => {
      await api('/api/auth/refresh', { method: 'POST' });
      await load();
      setMessage('New access and refresh tokens issued. The previous refresh token is now revoked (rotation).');
    });

  const revoke = (session) =>
    run(async () => {
      await api(`/api/auth/sessions/${session.id}/revoke`, { method: 'POST' });
      if (session.current) {
        await logout();
        navigate('/login');
        return;
      }
      await load();
      setMessage(
        `Session ended. That device can't refresh any more; its current access token still works for up to ${info.access_token_lifetime / 60} minutes.`
      );
    });

  if (!info) return <p className="muted">{message || 'Loading…'}</p>;

  const accessLeft = accessDropped ? 0 : remaining(info.access_token);
  const refreshLeft = remaining(info.refresh_token);

  return (
    <div>
      <h1>Tokens &amp; sessions</h1>
      <p className="muted">Tokens are httpOnly cookies, so JavaScript can't read them; the backend decodes them for this page.</p>

      <div className="token-grid">
        <div className="card">
          <h2>Access token</h2>
          <p className={`countdown ${accessLeft === 0 ? 'expired' : ''}`}>{formatDuration(accessLeft)}</p>
          <dl>
            <dt>Issued</dt>
            <dd>{formatTime(info.access_token.issued_at)}</dd>
            <dt>Expires</dt>
            <dd>{formatTime(info.access_token.expires_at)}</dd>
            <dt>Lifetime</dt>
            <dd>{info.access_token_lifetime / 60} minutes</dd>
          </dl>
        </div>
        <div className="card">
          <h2>Refresh token</h2>
          {info.refresh_token ? (
            <>
              <p className="countdown">{formatDuration(refreshLeft)}</p>
              <dl>
                <dt>ID (jti)</dt>
                <dd><code>{info.refresh_token.jti.slice(0, 12)}…</code></dd>
                <dt>Issued</dt>
                <dd>{formatDateTime(info.refresh_token.issued_at)}</dd>
                <dt>Expires</dt>
                <dd>{formatDateTime(info.refresh_token.expires_at)}</dd>
              </dl>
            </>
          ) : (
            <p className="muted">No refresh token cookie.</p>
          )}
        </div>
      </div>

      <div className="actions">
        <button className="btn btn-outline" onClick={expireAccess} disabled={busy || accessDropped}>
          Expire access token now
        </button>
        <button className="btn btn-outline" onClick={callProtectedApi} disabled={busy}>
          Call protected API
        </button>
        <button className="btn btn-outline" onClick={refreshNow} disabled={busy}>
          Refresh tokens now
        </button>
      </div>
      {message && <p className="notice">{message}</p>}

      <h2>Active sessions</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Device</th>
              <th>Started</th>
              <th>Last refresh</th>
              <th>Refreshes</th>
              <th>Expires</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {info.sessions.map((s) => (
              <tr key={s.id}>
                <td>
                  {describeDevice(s.device)} {s.current && <span className="badge">This browser</span>}
                  <div className="muted small"><code>{s.id.slice(0, 8)}</code></div>
                </td>
                <td>{formatDateTime(s.started_at)}</td>
                <td>{formatTime(s.last_refreshed_at)}</td>
                <td>{s.refreshes}</td>
                <td>{formatDateTime(s.expires_at)}</td>
                <td>
                  <button className="btn btn-outline btn-small" onClick={() => revoke(s)} disabled={busy}>
                    {s.current ? 'Log out' : 'Revoke'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
