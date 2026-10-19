import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Review artifact only; never included in the desktop /app distribution.
export default defineConfig({
  plugins: [react()], base: "../",
  build: { outDir: "../folder-preview", emptyOutDir: true,
    rollupOptions: { input: "design/folders.html" } },
});
