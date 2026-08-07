import type { Mensaje } from './useChatStream';

interface Props {
  mensaje: Mensaje;
  compacto?: boolean;
}

export default function BurbujaMensaje({ mensaje, compacto = false }: Props) {
  const esUsuario = mensaje.rol === 'usuario';
  const esError = mensaje.rol === 'error';

  const clases = [
    'max-w-[80%] whitespace-pre-wrap rounded-2xl px-(--spacing-fluid-xs) py-(--spacing-fluid-2xs) text-sm overflow-hidden transition-[max-height] duration-300 ease-in-out',
    esUsuario
      ? 'bg-(--color-acento) text-white'
      : esError
        ? 'border border-red-200 bg-red-50 text-red-700'
        : 'border border-(--color-borde) bg-(--color-superficie) text-(--color-texto)',
  ].join(' ');

  return (
    <div class={`flex ${esUsuario ? 'justify-end' : 'justify-start'}`}>
      <div class={clases} style={{ maxHeight: compacto ? '1.25rem' : '40rem' }}>
        {mensaje.texto || ' '}
      </div>
    </div>
  );
}
