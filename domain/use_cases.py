"""
Casos de uso: orquestan entidades y puertos para resolver una acción
de negocio concreta. Esto es lo que el orquestador de agentes va a
invocar como "herramientas" (tools) del LLM.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from uuid import UUID

from .entities import (
    Cita,
    LineaPedido,
    Pedido,
    SlotDisponible,
)
from .exceptions import ProfesionalNoDisponible, ServicioNoExiste
from .ports import (
    RepositorioCitas,
    RepositorioClientes,
    RepositorioConocimiento,
    RepositorioPedidos,
    RepositorioProfesionales,
    RepositorioServicios,
    SincronizadorCalendario,
)

logger = logging.getLogger(__name__)

# date.weekday(): 0=lunes ... 6=domingo. No usamos strftime('%A') porque
# depende del locale del sistema operativo y nunca coincidiría de forma
# fiable con los nombres en español usados en config/business.yaml.
_DIAS_SEMANA_ES = [
    "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo",
]


class ComprobarDisponibilidad:
    """Devuelve huecos libres para un servicio en una fecha dada,
    opcionalmente con un profesional concreto."""

    def __init__(
        self,
        servicios: RepositorioServicios,
        profesionales: RepositorioProfesionales,
        citas: RepositorioCitas,
    ):
        self._servicios = servicios
        self._profesionales = profesionales
        self._citas = citas

    def ejecutar(
        self, servicio_id: str, dia: date, profesional_id: str | None = None
    ) -> list[SlotDisponible]:
        servicio = self._servicios.obtener(servicio_id)
        if servicio is None:
            raise ServicioNoExiste(servicio_id)

        candidatos = (
            [self._profesionales.obtener(profesional_id)]
            if profesional_id
            else self._profesionales.listar_por_servicio(servicio_id)
        )
        candidatos = [p for p in candidatos if p is not None]

        dia_semana = _DIAS_SEMANA_ES[dia.weekday()]
        slots: list[SlotDisponible] = []

        for prof in candidatos:
            horario = prof.horario_semanal.get(dia_semana)
            if not horario:
                continue
            inicio_jornada, fin_jornada = horario
            ocupadas = self._citas.citas_de_profesional_en_fecha(prof.id, dia)

            cursor = datetime.combine(dia, inicio_jornada)
            fin_jornada_dt = datetime.combine(dia, fin_jornada)
            duracion = timedelta(minutes=servicio.duracion_minutos)

            while cursor + duracion <= fin_jornada_dt:
                solapa = any(
                    cursor < c.fin and (cursor + duracion) > c.inicio
                    for c in ocupadas
                )
                if not solapa:
                    slots.append(SlotDisponible(
                        profesional_id=prof.id,
                        inicio=cursor,
                        fin=cursor + duracion,
                    ))
                cursor += timedelta(minutes=15)  # granularidad de búsqueda

        return slots


class CrearReserva:
    def __init__(
        self,
        servicios: RepositorioServicios,
        profesionales: RepositorioProfesionales,
        citas: RepositorioCitas,
        clientes: RepositorioClientes,
        disponibilidad: ComprobarDisponibilidad,
        calendario: SincronizadorCalendario | None = None,
    ):
        self._servicios = servicios
        self._profesionales = profesionales
        self._citas = citas
        self._clientes = clientes
        self._disponibilidad = disponibilidad
        self._calendario = calendario

    def ejecutar(
        self,
        servicio_id: str,
        profesional_id: str,
        cliente_id: str,
        inicio: datetime,
    ) -> Cita:
        servicio = self._servicios.obtener(servicio_id)
        if servicio is None:
            raise ServicioNoExiste(servicio_id)

        fin = inicio + timedelta(minutes=servicio.duracion_minutos)

        libres = self._disponibilidad.ejecutar(
            servicio_id, inicio.date(), profesional_id
        )
        cabe = any(s.inicio <= inicio and s.fin >= fin for s in libres)
        if not cabe:
            raise ProfesionalNoDisponible(profesional_id, inicio)

        cita = Cita.nueva(servicio_id, profesional_id, cliente_id, inicio, fin)

        if self._calendario is not None:
            # Best-effort: un fallo al sincronizar con el calendario externo
            # no debe impedir crear la reserva en el sistema.
            try:
                profesional = self._profesionales.obtener(profesional_id)
                if profesional is not None:
                    cita.evento_calendario_id = self._calendario.crear_evento(
                        cita, servicio, profesional
                    )
            except Exception:
                logger.exception(
                    "No se pudo sincronizar la cita %s con el calendario externo",
                    cita.id,
                )

        self._citas.guardar(cita)
        return cita


class CancelarReserva:
    def __init__(
        self,
        citas: RepositorioCitas,
        calendario: SincronizadorCalendario | None = None,
    ):
        self._citas = citas
        self._calendario = calendario

    def ejecutar(self, cita_id: UUID) -> None:
        if self._calendario is not None:
            cita = self._citas.obtener(cita_id)
            if cita is not None and cita.evento_calendario_id:
                try:
                    self._calendario.cancelar_evento(cita.evento_calendario_id)
                except Exception:
                    logger.exception(
                        "No se pudo cancelar en el calendario externo el "
                        "evento de la cita %s",
                        cita_id,
                    )

        self._citas.cancelar(cita_id)


class RegistrarPedido:
    def __init__(self, pedidos: RepositorioPedidos, servicios: RepositorioServicios):
        self._pedidos = pedidos
        self._servicios = servicios

    def ejecutar(self, cliente_id: str, lineas: list[LineaPedido]) -> Pedido:
        for linea in lineas:
            if self._servicios.obtener(linea.servicio_id) is None:
                raise ServicioNoExiste(linea.servicio_id)
        pedido = Pedido.nuevo(cliente_id, lineas)
        self._pedidos.guardar(pedido)
        return pedido


class ConsultarConocimientoNegocio:
    """Caso de uso puente hacia el RAG: dado que la respuesta depende
    de contenido documental (precios, políticas, horarios generales),
    delega en el puerto de conocimiento."""

    def __init__(self, conocimiento: RepositorioConocimiento):
        self._conocimiento = conocimiento

    def ejecutar(self, consulta: str) -> dict:
        resultados = self._conocimiento.buscar_con_fuentes(consulta)
        fragmentos = [r["texto"] for r in resultados]

        # Las fuentes solo se exponen si la nota de origen está marcada
        # como pública: el RAG puede seguir usando fragmentos de notas
        # internas para responder en texto, pero su fichero nunca sale
        # como "fuente" resaltable si no es publicar_web: true.
        fuentes = []
        vistas = set()
        for r in resultados:
            fuente = r.get("fuente")
            if fuente and r.get("publicar_web") is True and fuente not in vistas:
                vistas.add(fuente)
                fuentes.append({"fuente": fuente, "categoria": r.get("categoria")})

        return {"fragmentos": fragmentos, "fuentes": fuentes}
