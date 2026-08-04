# Orquestador agéntico — esqueleto hexagonal

Esqueleto funcional de un orquestador de agentes con arquitectura
hexagonal (puertos y adaptadores), pensado para negocios "AI-first"
donde el chat es el producto principal y la web es secundaria.

## Estructura

```
domain/           → entidades, puertos (interfaces) y casos de uso.
                     Sin dependencias externas. Esto es lo único que
                     cambia de verdad entre negocios.
application/       → orquestador de agentes, definición de tools,
                     construcción del system prompt.
adapters/in_/      → adaptadores de entrada: FastAPI (chat web),
                     Telegram.
adapters/out/      → adaptadores de salida: LLM (Anthropic), vector
                     store (Chroma) + ingesta de Obsidian,
                     repositorios en memoria (sustituibles por
                     Postgres sin tocar el dominio).
config/            → configuración declarativa por negocio (YAML)
                     + loader.
main.py            → composition root: conecta todas las piezas.
```

## Puesta en marcha

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Copia .env.example a .env y rellena tus claves reales:
#   ANTHROPIC_API_KEY=sk-...
#   TELEGRAM_BOT_TOKEN=...   # opcional, solo si quieres el canal Telegram
cp .env.example .env

# 1. Prepara tu vault de Obsidian con el conocimiento del negocio
#    (precios, políticas, horarios, FAQs) en ./vault_negocio/*.md

# 2. Indexa el vault en el RAG
python -m adapters.out.obsidian_ingest --vault ./vault_negocio

# 3. Ajusta config/business.yaml con tus servicios y profesionales

# 4. Arranca el sistema
python main.py
```

El chat web queda disponible en `POST http://localhost:8000/chat`
con body `{"usuario_id": "...", "mensaje": "..."}`.

## Cómo extender a otro negocio

1. Duplica `config/business.yaml` y ajusta servicios/profesionales/tono.
2. Crea un nuevo vault de Obsidian con el conocimiento de ese negocio
   e indícalo en `vault_obsidian`.
3. Vuelve a correr la ingesta contra ese vault.
4. Si el negocio necesita un caso de uso distinto (p. ej. "reservar
   mesa" en vez de "reservar cita"), añádelo en `domain/use_cases.py`
   y expón su tool en `application/tools.py` — el resto del sistema
   no cambia.

## Cómo sustituir un adaptador

Ejemplo: pasar de repositorios en memoria a Postgres.

1. Crea `adapters/out/repositorios_postgres.py` implementando las
   mismas interfaces de `domain/ports.py` (`RepositorioCitas`, etc.)
2. En `main.py`, cambia la instanciación en `construir_sistema()`.
3. Nada en `domain/` ni en `application/` se modifica.

## Próximos pasos sugeridos

- Persistir las sesiones de conversación (Redis) en vez de memoria
  del proceso.
- Añadir autenticación/roles (propietario, empleado, cliente) para
  que el agente adapte qué herramientas y qué información expone
  según quién pregunta.
- Tests de los casos de uso de dominio (son puro Python, fáciles de
  testear sin mocks pesados).
- Adaptador de salida para notificaciones (confirmaciones de cita
  por Telegram/email) implementando `NotificadorMensajes`.
