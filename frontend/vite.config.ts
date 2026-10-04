import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/app/',
  build: { outDir: '../src/facetmark/web/dist', emptyOutDir: true, assetsDir: 'static' },
  server: { proxy: Object.fromEntries(['/app/boot', '/admin', '/bookmarks', '/bookmark', '/quick', '/search', '/suggest', '/sessions', '/session', '/stats', '/health', '/synthesize', '/open', '/link-health'].map(p => [p, 'http://127.0.0.1:8787'])) },
});
