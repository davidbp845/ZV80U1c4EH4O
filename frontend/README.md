# Frontend cliente — Astro + Preact

Web pública del negocio (Astro, salida estática) con un chat en
streaming (isla Preact) conectado al backend Python. Proyecto
hermano e independiente del backend salvo por las llamadas HTTP del
chat — ver la sección "Frontend cliente" en `../CLAUDE.md` para el
detalle de arquitectura (formato de los eventos SSE, convención
`publicar_web`, vínculo chat↔contenido, etc).

## Puesta en marcha

```bash
npm install
cp .env.example .env   # PUBLIC_API_BASE_URL, por defecto http://localhost:8000
npm run dev             # http://localhost:4321 — necesita el backend arrancado (../main.py)
npm run build            # genera ./dist, estático
```

## Estructura

```
src/content.config.ts        → content collection que lee ../vault_negocio
                                (solo notas con publicar_web: true)
src/lib/negocio.ts           → lee ../config/business.yaml en build-time
src/components/chat/         → isla Preact: ChatWidget, useChatStream (parseo SSE a mano)
src/components/ContenidoPublico/ → tarjetas de contenido público del vault
src/styles/global.css        → tokens Tailwind v4 con escala fluida estilo Utopia.fyi
```

## Comandos

| Comando | Acción |
| :--- | :--- |
| `npm run dev` | Servidor de desarrollo en `localhost:4321` |
| `npm run build` | Build estático de producción en `./dist/` |
| `npm run preview` | Sirve el build localmente antes de desplegar |
| `npx astro check` | Type-checking de `.astro`/`.ts`/`.tsx` |
