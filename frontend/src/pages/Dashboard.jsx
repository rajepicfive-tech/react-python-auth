import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { useAuth } from '../context/AuthContext.jsx';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api('/api/dashboard')
      .then(setData)
      .catch((err) => {
        if (err.status === 401) logout();
        else setError(err.message);
      });
  }, [logout]);

  return (
    <div>
      <h1>Dashboard</h1>
      <p className="muted">
        Signed in as <strong>{user.full_name}</strong> ({user.email})
      </p>

      {error && <p className="error">{error}</p>}
      {!data && !error && <p className="muted">Loading…</p>}

      {data && (
        <>
          <p>{data.message}</p>
          <div className="stats">
            {Object.entries(data.stats).map(([key, value]) => (
              <div key={key} className="card stat">
                <span className="stat-value">{value}</span>
                <span className="muted">{key.replace('_', ' ')}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
