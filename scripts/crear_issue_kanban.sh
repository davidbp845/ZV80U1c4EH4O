#!/usr/bin/env bash
# Requiere: gh CLI autenticado (gh auth login) con acceso al repo y al Project,
# y el extra "gh project" habilitado (viene con gh >= 2.x).
#
# Crea UN issue y lo añade al Project, dejándolo en la columna (Status) indicada.
# Pensado para invocarse issue a issue (a mano o pidiéndoselo a Claude Code),
# en vez de tener una lista de issues hardcodeada dentro del script.
#
# Uso:
#   ./crear_issue_kanban.sh "Título" "Cuerpo" "Estado" ["label1,label2"]
#
#   Estado debe ser una de las columnas ya existentes en el Project:
#     Backlog | Ready | "In Progress" | "In Review" | Done
#
# Ejemplos:
#   ./crear_issue_kanban.sh "Tabla profesional_servicio (N:M)" \
#     "Al migrar persistencia a Postgres, añadir tabla intermedia profesional_servicio (relación N:M)." \
#     "Backlog"
#
#   ./crear_issue_kanban.sh "Mock de ProveedorLLM" \
#     "Confirmar resultado del mock: adapters/out/llm_mock.py, variable USE_MOCK_LLM." \
#     "In Progress" "enhancement"

set -euo pipefail

REPO="davidbp845/orquestador-serenidad"
OWNER="davidbp845"
PROJECT_NUMBER=1   # <-- ajusta esto al número real de tu Project (lo ves en la URL)

TITULO="${1:?Falta el título del issue}"
CUERPO="${2:?Falta el cuerpo del issue}"
ESTADO="${3:?Falta el estado (Backlog|Ready|\"In Progress\"|\"In Review\"|Done)}"
LABELS="${4:-}"

# 1. Crear el issue
ISSUE_ARGS=(--repo "$REPO" --title "$TITULO" --body "$CUERPO")
if [[ -n "$LABELS" ]]; then
  IFS=',' read -ra LABEL_ARR <<< "$LABELS"
  for l in "${LABEL_ARR[@]}"; do
    ISSUE_ARGS+=(--label "$l")
  done
fi

URL=$(gh issue create "${ISSUE_ARGS[@]}")
echo "Creado: $URL"

# 2. Añadirlo al Project (las columnas Backlog/Ready/In Progress/In Review/Done
#    ya existen como opciones del campo "Status" del Project, no hace falta crearlas)
ITEM_ID=$(gh project item-add "$PROJECT_NUMBER" --owner "$OWNER" --url "$URL" --format json --jq '.id')

# 3. Localizar el campo "Status" y la opción correspondiente al Estado pedido
FIELD_JSON=$(gh project field-list "$PROJECT_NUMBER" --owner "$OWNER" --format json)
FIELD_ID=$(echo "$FIELD_JSON" | jq -r '.fields[] | select(.name=="Status") | .id')
OPTION_ID=$(echo "$FIELD_JSON" | jq -r --arg estado "$ESTADO" '.fields[] | select(.name=="Status") | .options[] | select(.name==$estado) | .id')

if [[ -z "$FIELD_ID" || -z "$OPTION_ID" ]]; then
  echo "Aviso: no se encontró el campo Status o la columna '$ESTADO' en el Project #$PROJECT_NUMBER."
  echo "El issue se ha creado y añadido al Project, pero sin columna asignada."
  exit 0
fi

PROJECT_ID=$(gh project view "$PROJECT_NUMBER" --owner "$OWNER" --format json --jq '.id')

gh project item-edit \
  --project-id "$PROJECT_ID" \
  --id "$ITEM_ID" \
  --field-id "$FIELD_ID" \
  --single-select-option-id "$OPTION_ID"

echo "Añadido al Project #$PROJECT_NUMBER en la columna '$ESTADO'."
