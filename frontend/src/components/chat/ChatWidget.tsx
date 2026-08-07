import { useEffect, useLayoutEffect, useRef, useState } from 'preact/hooks';
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
  const [expandido, setExpandido] = useState(true);
  const finRef = useRef<HTMLDivElement>(null);
  const medidorRef = useRef<HTMLDivElement>(null);
  // Altura real de "sugerencias comprimidas" (intro + 1 fila de 2
  // botones), medida contra una réplica oculta siempre montada — así
  // conversación comprimida puede usar exactamente esa misma altura sin
  // depender de un valor fijo a mano que se desincronice si cambia el
  // diseño de las sugerencias.
  const [altoComprimido, setAltoComprimido] = useState<number | null>(null);
  // Tres modos distintos:
  // - Proponiendo preguntas, expandido: el área se ajusta al contenido
  //   (9 sugerencias). Correcto, sin cambios.
  // - Proponiendo preguntas, comprimido: solo 1 fila (2 sugerencias) —
  //   define "la altura comprimida" que se mide arriba.
  // - Conversación real, expandido: alto fijo grande (los mismos
  //   tamaños que ya se usaban antes del botón de comprimir).
  // - Conversación real, comprimido: la MISMA altura que "sugerencias
  //   comprimidas", sea cual sea el número de mensajes — con scroll
  //   vertical (ya autoscrollado al final) enseñando solo lo último.
  const hayConversacion = mensajes.length > 0;
  const primeraFilaSugerencias = SUGERENCIAS.slice(0, 2);
  const restoSugerencias = SUGERENCIAS.slice(2);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [mensajes, expandido]);

  useLayoutEffect(() => {
    const medir = () => {
      if (medidorRef.current) setAltoComprimido(medidorRef.current.offsetHeight);
    };
    medir();
    window.addEventListener('resize', medir);
    return () => window.removeEventListener('resize', medir);
  }, []);

  const manejarEnvio = (evento: Event) => {
    evento.preventDefault();
    const texto_ = texto.trim();
    if (!texto_ || enviando) return;
    enviarMensaje(texto_);
    setTexto('');
  };

  const estiloAreaMensajes =
    hayConversacion && !expandido && altoComprimido
      ? { height: `${altoComprimido}px` }
      : undefined;

  return (
    <div class="relative flex flex-col overflow-hidden rounded-2xl border border-(--color-borde) bg-(--color-fondo)">
      {/* Réplica oculta de "sugerencias comprimidas" (intro + 1 fila),
          siempre montada, solo para medir su altura real y que
          conversación comprimida pueda igualarla exactamente. */}
      <div
        ref={medidorRef}
        aria-hidden="true"
        class="invisible absolute inset-x-0 top-0 -z-10 hidden p-(--spacing-fluid-s) sm:block"
      >
        <p class="text-base 2xl:text-lg">¿En qué podemos ayudarte? Prueba con algo así:</p>
        <div class="mt-(--spacing-fluid-2xs) grid grid-cols-2 gap-(--spacing-fluid-2xs)">
          {primeraFilaSugerencias.map((sugerencia) => (
            <button
              key={sugerencia}
              type="button"
              tabIndex={-1}
              class="rounded-xl border px-(--spacing-fluid-xs) py-(--spacing-fluid-3xs) text-left text-sm 2xl:text-base"
            >
              {sugerencia}
            </button>
          ))}
        </div>
      </div>
      <div
        style={estiloAreaMensajes}
        class={`space-y-(--spacing-fluid-2xs) overflow-y-auto p-(--spacing-fluid-s) ${
          hayConversacion
            ? expandido
              ? 'h-[min(70vh,32rem)] lg:h-[min(70vh,36rem)] 2xl:h-[min(70vh,44rem)]'
              : ''
            : 'max-h-[min(70vh,32rem)] lg:max-h-[min(70vh,36rem)] 2xl:max-h-[min(70vh,44rem)]'
        }`}
      >
        {mensajes.length === 0 && (
          <div class="text-center">
            <p class="text-sm text-(--color-texto-suave) sm:hidden">
              Pregúntanos por precios, horarios o disponibilidad.
            </p>
            <div class="hidden sm:block">
              <p class="text-base text-(--color-texto-suave) 2xl:text-lg">
                ¿En qué podemos ayudarte? Prueba con algo así:
              </p>
              <div
                class={`grid grid-cols-2 gap-(--spacing-fluid-2xs) transition-[margin-top] duration-300 ease-in-out ${expandido ? 'mt-(--spacing-fluid-s)' : 'mt-(--spacing-fluid-2xs)'}`}
              >
                {primeraFilaSugerencias.map((sugerencia) => (
                  <button
                    key={sugerencia}
                    type="button"
                    onClick={() => enviarMensaje(sugerencia)}
                    disabled={enviando}
                    class={`rounded-xl border border-(--color-borde) bg-(--color-superficie) px-(--spacing-fluid-xs) text-left text-sm text-(--color-texto) transition-all duration-300 ease-in-out hover:border-(--color-acento) hover:bg-(--color-acento-suave) disabled:opacity-40 2xl:text-base ${expandido ? 'py-(--spacing-fluid-2xs)' : 'py-(--spacing-fluid-3xs)'}`}
                  >
                    {sugerencia}
                  </button>
                ))}
              </div>
              <div
                class="grid transition-[grid-template-rows] duration-300 ease-in-out"
                style={{ gridTemplateRows: expandido ? '1fr' : '0fr' }}
              >
                <div class="overflow-hidden">
                  <div
                    class="mt-(--spacing-fluid-2xs) grid grid-cols-2 gap-(--spacing-fluid-2xs) transition-opacity duration-300 ease-in-out"
                    style={{ opacity: expandido ? 1 : 0 }}
                  >
                    {restoSugerencias.map((sugerencia) => (
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
        <button
          type="button"
          onClick={() => setExpandido((v) => !v)}
          aria-label={expandido ? 'Comprimir respuesta' : 'Expandir respuesta'}
          title={expandido ? 'Comprimir respuesta' : 'Expandir respuesta'}
          class="inline-flex shrink-0 items-center justify-center rounded-full border border-(--color-borde) bg-(--color-superficie) p-(--spacing-fluid-3xs) text-(--color-texto-suave) transition-colors hover:border-(--color-acento) hover:text-(--color-acento)"
        >
          <svg
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="transition-transform duration-300 ease-in-out"
            style={{ transform: expandido ? 'scale(1)' : 'scale(0.9)' }}
          >
            {expandido ? (
              <path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7" />
            ) : (
              <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
            )}
          </svg>
        </button>
      </form>
    </div>
  );
}
