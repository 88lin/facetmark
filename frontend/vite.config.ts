import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  base: '/app/',
  build: { outDir: '../src/facetmark/web/dist', emptyOutDir: true, assetsDir: 'static' },
  server: { proxy: Object.fromEntries(['/app/boot', '/admin', '/bookmarks', '/bookmark', '/quick', '/search', '/suggest', '/sessions', '/session', '/stats', '/health', '/synthesize', '/open', '/link-health'].map(p => [p, 'http://127.0.0.1:8787'])) },
});
