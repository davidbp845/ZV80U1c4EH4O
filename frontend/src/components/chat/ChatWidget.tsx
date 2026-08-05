import { useEffect, useRef, useState } from 'preact/hooks';
import BurbujaMensaje from './BurbujaMensaje';
import IndicadorEscribiendo from './IndicadorEscribiendo';
import { useChatStream } from './useChatStream';

interface Props {
  apiBaseUrl: string;
}

export default function ChatWidget({ apiBaseUrl }: Props) {
  const { mensajes, enviando, enviarMensaje } = useChatStream(apiBaseUrl);
  const [texto, setTexto] = useState('');
  const finRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [mensajes]);

  const manejarEnvio = (evento: Event) => {
    evento.preventDefault();
    const texto_ = texto.trim();
    if (!texto_ || enviando) return;
    enviarMensaje(texto_);
    setTexto('');
  };

  return (
    <div class="flex h-[70vh] max-h-[32rem] flex-col overflow-hidden rounded-2xl border border-(--color-borde) bg-(--color-fondo)">
      <div class="flex-1 space-y-(--spacing-fluid-2xs) overflow-y-auto p-(--spacing-fluid-s)">
        {mensajes.length === 0 && (
          <p class="text-center text-sm text-(--color-texto-suave)">
            Pregúntanos por precios, horarios o disponibilidad.
          </p>
        )}
        {mensajes.map((m) =>
          m.rol === 'asistente' && m.enCurso && m.texto === '' ? (
            <IndicadorEscribiendo key={m.id} />
          ) : (
            <BurbujaMensaje key={m.id} mensaje={m} />
          ),
        )}
        <div ref={finRef} />
      </div>
      <form
        onSubmit={manejarEnvio}
        class="flex gap-(--spacing-fluid-2xs) border-t border-(--color-borde) p-(--spacing-fluid-2xs)"
      >
        <input
          value={texto}
          onInput={(e) => setTexto((e.target as HTMLInputElement).value)}
          placeholder="Escribe tu mensaje…"
          class="flex-1 rounded-full border border-(--color-borde) bg-(--color-superficie) px-(--spacing-fluid-xs) py-(--spacing-fluid-3xs) text-sm text-(--color-texto) outline-none focus:border-(--color-acento)"
        />
        <button
          type="submit"
          disabled={enviando || !texto.trim()}
          class="rounded-full bg-(--color-acento) px-(--spacing-fluid-s) py-(--spacing-fluid-3xs) text-sm font-medium text-white disabled:opacity-40"
        >
          Enviar
        </button>
      </form>
    </div>
  );
}
