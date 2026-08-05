import { useEffect, useRef, useState } from 'preact/hooks';
import BurbujaMensaje from './BurbujaMensaje';
import IndicadorEscribiendo from './IndicadorEscribiendo';
import { useChatStream } from './useChatStream';

interface Props {
  apiBaseUrl: string;
}

// Ejemplos de preguntas que cubren lo que el asistente sabe hacer hoy
// (tools de application/tools.py + contenido del vault). Solo se
// muestran como sugerencias clicables a partir de sm: en móvil el
// hueco es demasiado justo y priorizamos que el campo de texto quede
// siempre visible sin hacer scroll.
const SUGERENCIAS = [
  '¿Cuánto cuesta el masaje relajante de 60 min?',
  '¿Tenéis hueco mañana por la tarde?',
  '¿Cuál es vuestro horario de apertura?',
  '¿Dónde estáis ubicados?',
  '¿Tenéis alguna promoción activa?',
  '¿Puedo cancelar mi cita sin coste?',
  '¿Es seguro el masaje si estoy embarazada?',
  '¿Quién es la profesional que me atenderá?',
  'Quiero reservar un masaje descontracturante',
];

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
    <div class="flex h-[70vh] max-h-[32rem] flex-col overflow-hidden rounded-2xl border border-(--color-borde) bg-(--color-fondo) lg:max-h-[36rem] 2xl:max-h-[44rem]">
      <div class="flex-1 space-y-(--spacing-fluid-2xs) overflow-y-auto p-(--spacing-fluid-s)">
        {mensajes.length === 0 && (
          <div class="text-center">
            <p class="text-sm text-(--color-texto-suave) sm:hidden">
              Pregúntanos por precios, horarios o disponibilidad.
            </p>
            <div class="hidden sm:block">
              <p class="text-base text-(--color-texto-suave) 2xl:text-lg">
                ¿En qué podemos ayudarte? Prueba con algo así:
              </p>
              <div class="mt-(--spacing-fluid-s) grid grid-cols-2 gap-(--spacing-fluid-2xs)">
                {SUGERENCIAS.map((sugerencia) => (
                  <button
                    key={sugerencia}
                    type="button"
                    onClick={() => enviarMensaje(sugerencia)}
                    disabled={enviando}
                    class="rounded-xl border border-(--color-borde) bg-(--color-superficie) px-(--spacing-fluid-xs) py-(--spacing-fluid-2xs) text-left text-sm text-(--color-texto) transition-colors hover:border-(--color-acento) hover:bg-(--color-acento-suave) disabled:opacity-40 2xl:text-base"
                  >
                    {sugerencia}
                  </button>
                ))}
              </div>
            </div>
          </div>
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
