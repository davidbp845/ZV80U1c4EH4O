// @ts-check
import { defineConfig } from 'astro/config';

import preact from '@astrojs/preact';
import tailwindcss from '@tailwindcss/vite';

import sitemap from '@astrojs/sitemap';

// https://astro.build/config
export default defineConfig({
  // TODO: sustituir por el dominio real de producción en cuanto exista
  // (necesario para que @astrojs/sitemap y las URLs canónicas/OG generen
  // absolutas en vez de relativas).
  site: process.env.SITE_URL ?? 'https://centro-masajes-serenidad.example',

  integrations: [preact(), sitemap()],

  vite: {
    plugins: [tailwindcss()]
  }
});