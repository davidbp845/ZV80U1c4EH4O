import { useCallback, useRef, useState } from 'preact/hooks';

export interface Mensaje {
  id: string;
  rol: 'usuario' | 'asistente' | 'error';
  texto: string;
  enCurso?: boolean;
}

interface FuenteRag {
  fuente: string;
  categoria?: string | null;
}

const CLAVE_USUARIO_ID = 'orquestador_usuario_id';

function obtenerUsuarioId(): string {
  let id = localStorage.getItem(CLAVE_USUARIO_ID);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(CLAVE_USUARIO_ID, id);
  }
  return id;
}

function parsearFrameSSE(frame: string): { evento: string; data: string } | null {
  let evento = 'message';
  let data = '';
  for (const linea of frame.split('\n')) {
    if (linea.startsWith('event: ')) evento = linea.slice('event: '.length);
    else if (linea.startsWith('data: ')) data = linea.slice('data: '.length);
  }
  return data ? { evento, data } : null;
}

export function useChatStream(apiBaseUrl: string) {
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  const [enviando, setEnviando] = useState(false);
  const usuarioIdRef = useRef<string | null>(null);

  const enviarMensaje = useCallback(
    async (texto: string) => {
      if (!texto.trim() || enviando) return;
      if (!usuarioIdRef.current) usuarioIdRef.current = obtenerUsuarioId();

      const idAsistente = crypto.randomUUID();
      setMensajes((prev) => [
        ...prev,
        { id: crypto.randomUUID(), rol: 'usuario', texto },
        { id: idAsistente, rol: 'asistente', texto: '', enCurso: true },
      ]);
      setEnviando(true);

      const actualizarAsistente = (cambios: Partial<Mensaje>) => {
        setMensajes((prev) =>
          prev.map((m) => (m.id === idAsistente ? { ...m, ...cambios } : m)),
        );
      };

      try {
        // EventSource no soporta POST con body, así que el stream SSE
        // se lee y se parsea a mano desde el ReadableStream de fetch.
        const respuesta = await fetch(`${apiBaseUrl}/chat/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ usuario_id: usuarioIdRef.current, mensaje: texto }),
        });

        if (!respuesta.ok || !respuesta.body) {
          throw new Error(`El servidor respondió ${respuesta.status}`);
        }

        const lector = respuesta.body.getReader();
        const decodificador = new TextDecoder();
        let buffer = '';
        let fuentes: FuenteRag[] = [];

        while (true) {
          const { done, value } = await lector.read();
          if (done) break;
          buffer += decodificador.decode(value, { stream: true });

          let indiceSeparador: number;
          while ((indiceSeparador = buffer.indexOf('\n\n')) !== -1) {
            const frame = buffer.slice(0, indiceSeparador);
            buffer = buffer.slice(indiceSeparador + 2);
            const evento = parsearFrameSSE(frame);
            if (!evento) continue;

            if (evento.evento === 'delta') {
              const { texto: delta } = JSON.parse(evento.data);
              setMensajes((prev) =>
                prev.map((m) =>
                  m.id === idAsistente ? { ...m, texto: m.texto + delta } : m,
                ),
              );
            } else if (evento.evento === 'fuentes') {
              fuentes = JSON.parse(evento.data).fuentes ?? [];
            } else if (evento.evento === 'done') {
              actualizarAsistente({ enCurso: false });
              if (fuentes.length > 0) {
                window.dispatchEvent(
                  new CustomEvent('orquestador:fuentes', { detail: fuentes }),
                );
              }
            } else if (evento.evento === 'error') {
              const { mensaje } = JSON.parse(evento.data);
              actualizarAsistente({ rol: 'error', texto: mensaje, enCurso: false });
            }
          }
        }
      } catch {
        actualizarAsistente({
          rol: 'error',
          texto: 'No se ha podido contactar con el asistente. Inténtalo de nuevo.',
          enCurso: false,
        });
      } finally {
        setEnviando(false);
      }
    },
    [apiBaseUrl, enviando],
  );

  return { mensajes, enviando, enviarMensaje };
}
