// @ts-check
import { defineConfig } from 'astro/config';

import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  output: 'static',
  build: {
    inlineStylesheets: 'always',
  },
  vite: {
    server: {
      proxy: {
        '/api': { target: 'http://localhost:8000', changeOrigin: true },
        '/shiny': { target: 'http://localhost:8000', changeOrigin: true, ws: true },
      },
    },

    plugins: [tailwindcss()],
  },
});