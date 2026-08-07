import type { APIRoute } from 'astro';

// Generado en vez de un public/robots.txt estático para que el Sitemap
// apunte siempre al mismo `site` configurado en astro.config.mjs
// (el placeholder de hoy o el dominio real, cuando se defina).
export const GET: APIRoute = ({ site }) => {
  const sitemapUrl = new URL('sitemap-index.xml', site);

  return new Response(`User-agent: *\nAllow: /\n\nSitemap: ${sitemapUrl.href}\n`, {
    headers: { 'Content-Type': 'text/plain' },
  });
};
