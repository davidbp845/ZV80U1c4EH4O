// A partir del cuerpo Markdown crudo de una nota (sin frontmatter),
// extrae un título (primer H1) y un extracto de texto plano para las
// tarjetas de la sección de contenido público.
export function extraerTitulo(body: string, idFallback: string): string {
  const match = body.match(/^#\s+(.+)$/m);
  return match ? match[1].trim() : idFallback;
}

export function extraerResumen(body: string, longitudMaxima = 160): string {
  const sinTitulo = body.replace(/^#\s+.+$/m, '');
  const primerParrafo = sinTitulo
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .find((p) => p.length > 0 && !p.startsWith('#'));

  if (!primerParrafo) return '';

  const textoPlano = primerParrafo
    .replace(/^#+\s*/, '')
    .replace(/[*_`]/g, '')
    .replace(/\s+/g, ' ')
    .trim();

  return textoPlano.length > longitudMaxima
    ? `${textoPlano.slice(0, longitudMaxima).trimEnd()}…`
    : textoPlano;
}
