"""Carga la config YAML del negocio y construye las entidades base
(servicios, profesionales) que alimentan los repositorios en memoria."""
from __future__ import annotations

from datetime import time

import yaml
from pydantic import ValidationError

from config.schema import ConfigNegocio
from domain.entities import Profesional, Servicio


def cargar_config(ruta: str) -> dict:
    with open(ruta, encoding="utf-8") as f:
        datos = yaml.safe_load(f)

    try:
        config = ConfigNegocio.model_validate(datos)
    except ValidationError as exc:
        raise ValueError(f"Configuración inválida en {ruta}:\n{exc}") from exc

    return config.model_dump()


def _parse_hora(valor: str) -> time:
    h, m = valor.split(":")
    return time(int(h), int(m))


def construir_servicios(config: dict) -> list[Servicio]:
    return [
        Servicio(
            id=s["id"],
            nombre=s["nombre"],
            duracion_minutos=s["duracion_minutos"],
            precio=s["precio"],
        )
        for s in config.get("servicios", [])
    ]


def construir_profesionales(config: dict) -> list[Profesional]:
    profesionales = []
    for p in config.get("profesionales", []):
        horario = {
            dia: (_parse_hora(rango[0]), _parse_hora(rango[1]))
            for dia, rango in p.get("horario_semanal", {}).items()
        }
        profesionales.append(Profesional(
            id=p["id"],
            nombre=p["nombre"],
            servicios_ids=p.get("servicios_ids", []),
            horario_semanal=horario,
        ))
    return profesionales
