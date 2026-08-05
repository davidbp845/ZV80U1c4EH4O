export default function IndicadorEscribiendo() {
  return (
    <div class="flex justify-start">
      <div class="flex items-center gap-1 rounded-2xl border border-(--color-borde) bg-(--color-superficie) px-(--spacing-fluid-xs) py-(--spacing-fluid-2xs)">
        <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-(--color-texto-suave) [animation-delay:-0.3s]" />
        <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-(--color-texto-suave) [animation-delay:-0.15s]" />
        <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-(--color-texto-suave)" />
      </div>
    </div>
  );
}
