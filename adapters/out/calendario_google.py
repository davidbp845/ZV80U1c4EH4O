"""Adaptador de SincronizadorCalendario contra Google Calendar.

Se autentica con una cuenta de servicio (no con el flujo OAuth de un
usuario): el calendario del negocio debe compartirse manualmente con el
email de esa cuenta de servicio (campo `client_email` del JSON de
credenciales) para que pueda crear/cancelar eventos en él."""
from __future__ import annotations

from google.oauth2 import service_account
from googleapiclient.discovery import build

from domain.entities import Cita, Profesional, Servicio
from domain.ports import SincronizadorCalendario

_SCOPES = ["https://www.googleapis.com/auth/calendar"]


class SincronizadorCalendarioGoogle(SincronizadorCalendario):
    def __init__(
        self,
        credenciales_json_path: str,
        calendar_id: str,
        zona_horaria: str = "Europe/Madrid",
    ):
        credenciales = service_account.Credentials.from_service_account_file(
            credenciales_json_path, scopes=_SCOPES
        )
        self._servicio = build("calendar", "v3", credentials=credenciales)
        self._calendar_id = calendar_id
        self._zona_horaria = zona_horaria

    def crear_evento(
        self, cita: Cita, servicio: Servicio, profesional: Profesional
    ) -> str:
        # Las fechas de dominio son naive (sin tz, hora local implícita del
        # negocio) — la API de Google exige timeZone explícito si el
        # dateTime no lleva offset, si no rechaza el evento (400).
        evento = {
            "summary": f"{servicio.nombre} — {profesional.nombre}",
            "description": f"Cliente: {cita.cliente_id}",
            "start": {"dateTime": cita.inicio.isoformat(), "timeZone": self._zona_horaria},
            "end": {"dateTime": cita.fin.isoformat(), "timeZone": self._zona_horaria},
        }
        creado = (
            self._servicio.events()
            .insert(calendarId=self._calendar_id, body=evento)
            .execute()
        )
        return creado["id"]

    def cancelar_evento(self, evento_id: str) -> None:
        self._servicio.events().delete(
            calendarId=self._calendar_id, eventId=evento_id
        ).execute()
