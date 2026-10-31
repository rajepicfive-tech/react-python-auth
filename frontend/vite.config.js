import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Serve the API from the same origin as the app, so auth cookies are first-party.
    // In production, put a reverse proxy (e.g. nginx) in front of both.
    proxy: { '/api': 'http://localhost:8000' },
  },
});
