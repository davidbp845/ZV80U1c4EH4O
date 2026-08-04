"""
Composition root: aquí, y solo aquí, se conocen todas las
implementaciones concretas. Se instancian los adaptadores y se
inyectan en los casos de uso y en el orquestador. Si mañana cambias
Chroma por Qdrant, o Telegram por WhatsApp, este es el único fichero
que toca saberlo.
"""
from __future__ import annotations

import threading

from dotenv import load_dotenv

load_dotenv()  # lee .env si existe; si las variables ya están exportadas
                # en el entorno (ej. en producción), esas tienen prioridad
                # y load_dotenv() no las sobreescribe por defecto.

import uvicorn

from adapters.in_.fastapi_app import crear_router
from adapters.in_.telegram_bot import crear_bot
from adapters.out.llm_anthropic import ProveedorLLMAnthropic
from adapters.out.repositorios_memoria import (
    RepositorioCitasMemoria, RepositorioClientesMemoria,
    RepositorioPedidosMemoria, RepositorioProfesionalesMemoria,
    RepositorioServiciosMemoria,
)
from adapters.out.vector_store import RepositorioConocimientoChroma
from application.orchestrator import OrquestadorAgente
from application.prompts import construir_system_prompt
from application.tools import EjecutorHerramientas
from config.loader import cargar_config, construir_profesionales, construir_servicios
from domain.use_cases import (
    CancelarReserva, ComprobarDisponibilidad, ConsultarConocimientoNegocio,
    CrearReserva, RegistrarPedido,
)


def construir_sistema(ruta_config: str = "config/business.yaml") -> OrquestadorAgente:
    config = cargar_config(ruta_config)

    # --- Repositorios (adaptadores de salida) ---
    repo_servicios = RepositorioServiciosMemoria(construir_servicios(config))
    repo_profesionales = RepositorioProfesionalesMemoria(construir_profesionales(config))
    repo_citas = RepositorioCitasMemoria()
    repo_clientes = RepositorioClientesMemoria()
    repo_pedidos = RepositorioPedidosMemoria()
    conocimiento = RepositorioConocimientoChroma()
    llm = ProveedorLLMAnthropic()

    # --- Casos de uso (dominio) ---
    disponibilidad = ComprobarDisponibilidad(repo_servicios, repo_profesionales, repo_citas)
    crear_reserva = CrearReserva(repo_servicios, repo_citas, repo_clientes, disponibilidad)
    cancelar_reserva = CancelarReserva(repo_citas)
    registrar_pedido = RegistrarPedido(repo_pedidos, repo_servicios)
    consultar_conocimiento = ConsultarConocimientoNegocio(conocimiento)

    ejecutor = EjecutorHerramientas({
        "comprobar_disponibilidad": disponibilidad,
        "crear_reserva": crear_reserva,
        "cancelar_reserva": cancelar_reserva,
        "registrar_pedido": registrar_pedido,
        "consultar_conocimiento": consultar_conocimiento,
    })

    system_prompt = construir_system_prompt(config)

    return OrquestadorAgente(llm=llm, ejecutor_herramientas=ejecutor, system_prompt=system_prompt), config


def main():
    orquestador, config = construir_sistema()

    app = crear_router(orquestador)

    hilo_web = threading.Thread(
        target=lambda: uvicorn.run(app, host="0.0.0.0", port=8000),
        daemon=True,
    )
    hilo_web.start()
    print("Chat web disponible en http://localhost:8000/chat")

    if config.get("canales", {}).get("telegram"):
        import os
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if token:
            bot = crear_bot(token, orquestador)
            print("Bot de Telegram iniciado.")
            bot.run_polling()
        else:
            print("TELEGRAM_BOT_TOKEN no definido: bot de Telegram no arrancado.")
            hilo_web.join()
    else:
        hilo_web.join()


if __name__ == "__main__":
    main()
