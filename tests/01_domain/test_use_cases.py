"""Tests de casos de uso de dominio usando fakes en memoria que
implementan los puertos de domain/ports.py — sin mocks pesados, tal
y como sugiere el README."""
from datetime import date, datetime, time

import pytest

from domain.entities import Cita, LineaPedido, Profesional, Servicio
from domain.exceptions import ProfesionalNoDisponible, ServicioNoExiste
from domain.use_cases import (
    _DIAS_SEMANA_ES,
    CancelarReserva,
    ComprobarDisponibilidad,
    ConsultarConocimientoNegocio,
    CrearReserva,
    RegistrarPedido,
)


class FakeRepoServicios:
    def __init__(self, servicios=None):
        self._data = {s.id: s for s in (servicios or [])}

    def obtener(self, servicio_id):
        return self._data.get(servicio_id)

    def listar(self):
        return list(self._data.values())


class FakeRepoProfesionales:
    def __init__(self, profesionales=None):
        self._data = {p.id: p for p in (profesionales or [])}

    def obtener(self, profesional_id):
        return self._data.get(profesional_id)

    def listar_por_servicio(self, servicio_id):
        return [p for p in self._data.values() if servicio_id in p.servicios_ids]


class FakeRepoCitas:
    def __init__(self, citas=None):
        self._data = {c.id: c for c in (citas or [])}
        self.canceladas = []

    def guardar(self, cita):
        self._data[cita.id] = cita

    def citas_de_profesional_en_fecha(self, profesional_id, dia):
        return [
            c for c in self._data.values()
            if c.profesional_id == profesional_id and c.inicio.date() == dia
        ]

    def cancelar(self, cita_id):
        self.canceladas.append(cita_id)


class FakeRepoClientes:
    def __init__(self):
        self._data = {}

    def obtener(self, cliente_id):
        return self._data.get(cliente_id)

    def guardar(self, cliente):
        self._data[cliente.id] = cliente

    def buscar_por_telefono(self, telefono):
        return next((c for c in self._data.values() if c.telefono == telefono), None)


class FakeRepoPedidos:
    def __init__(self):
        self._data = {}

    def guardar(self, pedido):
        self._data[pedido.id] = pedido

    def obtener(self, pedido_id):
        return self._data.get(pedido_id)


class FakeRepoConocimiento:
    def __init__(self, resultados=None):
        self._resultados = resultados or []
        self.ultima_consulta = None

    def buscar(self, consulta, top_k=5):
        self.ultima_consulta = consulta
        return [r["texto"] for r in self._resultados]

    def buscar_con_fuentes(self, consulta, top_k=5):
        self.ultima_consulta = consulta
        return self._resultados


# Lunes cualquiera, para tener el nombre de día controlado.
_LUNES = date(2026, 8, 3)
assert _DIAS_SEMANA_ES[_LUNES.weekday()] == "lunes"


def _servicio(duracion=60):
    return Servicio(id="masaje", nombre="Masaje", duracion_minutos=duracion, precio=50.0)


def _profesional(horario=None):
    return Profesional(
        id="ana",
        nombre="Ana",
        servicios_ids=["masaje"],
        horario_semanal=horario or {"lunes": (time(9, 0), time(10, 0))},
    )


class TestComprobarDisponibilidad:
    def test_lanza_si_servicio_no_existe(self):
        caso = ComprobarDisponibilidad(
            FakeRepoServicios(), FakeRepoProfesionales(), FakeRepoCitas()
        )
        with pytest.raises(ServicioNoExiste):
            caso.ejecutar("no_existe", _LUNES)

    def test_genera_slots_segun_duracion_y_horario(self):
        caso = ComprobarDisponibilidad(
            FakeRepoServicios([_servicio(duracion=30)]),
            FakeRepoProfesionales([_profesional()]),
            FakeRepoCitas(),
        )
        slots = caso.ejecutar("masaje", _LUNES)

        inicios = [s.inicio.time() for s in slots]
        assert inicios == [time(9, 0), time(9, 15), time(9, 30)]
        assert all(s.profesional_id == "ana" for s in slots)

    def test_sin_horario_ese_dia_no_hay_slots(self):
        sin_horario = Profesional(id="ana", nombre="Ana", servicios_ids=["masaje"])
        caso = ComprobarDisponibilidad(
            FakeRepoServicios([_servicio(duracion=30)]),
            FakeRepoProfesionales([sin_horario]),
            FakeRepoCitas(),
        )
        assert caso.ejecutar("masaje", _LUNES) == []

    def test_respeta_citas_existentes(self):
        cita_existente = Cita.nueva(
            "masaje", "ana", "cliente1",
            datetime.combine(_LUNES, time(9, 30)),
            datetime.combine(_LUNES, time(10, 0)),
        )
        caso = ComprobarDisponibilidad(
            FakeRepoServicios([_servicio(duracion=30)]),
            FakeRepoProfesionales([_profesional()]),
            FakeRepoCitas([cita_existente]),
        )
        slots = caso.ejecutar("masaje", _LUNES)
        assert [s.inicio.time() for s in slots] == [time(9, 0)]

    def test_filtra_por_profesional_id_si_se_indica(self):
        otro = Profesional(
            id="beatriz", nombre="Beatriz", servicios_ids=["masaje"],
            horario_semanal={"lunes": (time(9, 0), time(10, 0))},
        )
        caso = ComprobarDisponibilidad(
            FakeRepoServicios([_servicio(duracion=30)]),
            FakeRepoProfesionales([_profesional(), otro]),
            FakeRepoCitas(),
        )
        slots = caso.ejecutar("masaje", _LUNES, profesional_id="beatriz")
        assert all(s.profesional_id == "beatriz" for s in slots)
        assert len(slots) == 3


class TestCrearReserva:
    def _construir(self, citas=None):
        repo_servicios = FakeRepoServicios([_servicio(duracion=30)])
        repo_citas = FakeRepoCitas(citas)
        repo_clientes = FakeRepoClientes()
        disponibilidad = ComprobarDisponibilidad(
            repo_servicios, FakeRepoProfesionales([_profesional()]), repo_citas
        )
        caso = CrearReserva(repo_servicios, repo_citas, repo_clientes, disponibilidad)
        return caso, repo_citas

    def test_lanza_si_servicio_no_existe(self):
        caso, _ = self._construir()
        with pytest.raises(ServicioNoExiste):
            caso.ejecutar("no_existe", "ana", "cliente1", datetime.combine(_LUNES, time(9, 0)))

    def test_crea_reserva_en_hueco_libre(self):
        caso, repo_citas = self._construir()
        inicio = datetime.combine(_LUNES, time(9, 0))

        cita = caso.ejecutar("masaje", "ana", "cliente1", inicio)

        assert cita.inicio == inicio
        assert cita.fin == datetime.combine(_LUNES, time(9, 30))
        assert repo_citas._data[cita.id] is cita

    def test_lanza_si_no_cabe_en_hueco(self):
        caso, _ = self._construir()
        # Fuera del horario laboral (09:00-10:00).
        inicio = datetime.combine(_LUNES, time(11, 0))
        with pytest.raises(ProfesionalNoDisponible):
            caso.ejecutar("masaje", "ana", "cliente1", inicio)

    def test_lanza_si_solapa_con_cita_existente(self):
        cita_existente = Cita.nueva(
            "masaje", "ana", "cliente0",
            datetime.combine(_LUNES, time(9, 0)),
            datetime.combine(_LUNES, time(9, 30)),
        )
        caso, _ = self._construir(citas=[cita_existente])
        with pytest.raises(ProfesionalNoDisponible):
            caso.ejecutar("masaje", "ana", "cliente1", datetime.combine(_LUNES, time(9, 0)))


class TestCancelarReserva:
    def test_delega_en_el_repositorio(self):
        repo_citas = FakeRepoCitas()
        caso = CancelarReserva(repo_citas)
        caso.ejecutar("cita-123")
        assert repo_citas.canceladas == ["cita-123"]


class TestRegistrarPedido:
    def test_registra_pedido_valido(self):
        repo_servicios = FakeRepoServicios([_servicio()])
        repo_pedidos = FakeRepoPedidos()
        caso = RegistrarPedido(repo_pedidos, repo_servicios)

        lineas = [LineaPedido(servicio_id="masaje", cantidad=2)]
        pedido = caso.ejecutar("cliente1", lineas)

        assert pedido.cliente_id == "cliente1"
        assert repo_pedidos._data[pedido.id] is pedido

    def test_lanza_si_alguna_linea_tiene_servicio_inexistente(self):
        repo_servicios = FakeRepoServicios([_servicio()])
        repo_pedidos = FakeRepoPedidos()
        caso = RegistrarPedido(repo_pedidos, repo_servicios)

        lineas = [LineaPedido(servicio_id="no_existe", cantidad=1)]
        with pytest.raises(ServicioNoExiste):
            caso.ejecutar("cliente1", lineas)


class TestConsultarConocimientoNegocio:
    def test_delega_la_busqueda_en_el_puerto(self):
        conocimiento = FakeRepoConocimiento(resultados=[
            {"texto": "fragmento 1", "fuente": "horarios.md", "categoria": "horarios", "publicar_web": True},
            {"texto": "fragmento 2", "fuente": "horarios.md", "categoria": "horarios", "publicar_web": True},
        ])
        caso = ConsultarConocimientoNegocio(conocimiento)

        resultado = caso.ejecutar("¿cuáles son los horarios?")

        assert resultado == {
            "fragmentos": ["fragmento 1", "fragmento 2"],
            "fuentes": [{"fuente": "horarios.md", "categoria": "horarios"}],
        }
        assert conocimiento.ultima_consulta == "¿cuáles son los horarios?"

    def test_no_expone_fuentes_de_notas_no_publicas(self):
        conocimiento = FakeRepoConocimiento(resultados=[
            {"texto": "fragmento interno", "fuente": "interno.md", "categoria": "interno", "publicar_web": False},
        ])
        caso = ConsultarConocimientoNegocio(conocimiento)

        resultado = caso.ejecutar("consulta interna")

        assert resultado["fragmentos"] == ["fragmento interno"]
        assert resultado["fuentes"] == []
