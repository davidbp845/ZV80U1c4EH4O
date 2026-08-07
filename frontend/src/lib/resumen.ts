// A partir del cuerpo Markdown crudo de una nota (sin frontmatter),
// extrae un título (primer H1) para las tarjetas de la sección de
// contenido público.
export function extraerTitulo(body: string, idFallback: string): string {
  const match = body.match(/^#\s+(.+)$/m);
  return match ? match[1].trim() : idFallback;
}
