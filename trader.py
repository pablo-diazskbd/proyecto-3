# trader.py

import time
import threading
import logging

from cliente import APIClient


class TradingBot:

    def __init__(self, nombre_grupo: str, base_url: str):

        self.nombre_grupo = nombre_grupo
        self.base_url = base_url

        self.api = APIClient(base_url)

        self.bot_id = None
        self.api_key = None

        self.running = True

        # Estado compartido (protegido por lock)
        self.market_state = {}
        self.lock = threading.Lock()

        # Flag para saber si ya ejecutamos al menos una orden (EP)
        self.orden_ejecutada = False

    # -------------------------------------------------
    # AUTENTICACION
    # -------------------------------------------------

    def autenticar(self) -> bool:

        body = {
            "nombre": self.nombre_grupo,
            "codigo": "clave-secreta"
        }

        response = self.api.post("/autenticar", json=body)

        if response is None:
            return False

        # Parseo seguro: .get() en vez de [] para evitar KeyError
        self.bot_id = response.get("bot_id")
        self.api_key = response.get("api_key")

        if not self.bot_id or not self.api_key:
            logging.error(f"Respuesta de autenticacion incompleta: {response}")
            return False

        self.api.set_api_key(self.api_key)

        logging.info(f"Autenticacion exitosa. bot_id={self.bot_id}")
        return True

    # -------------------------------------------------
    # ACEPTAR REGLAS
    # -------------------------------------------------

    def aceptar_reglas(self) -> bool:

        response = self.api.post("/aceptar_reglas")

        if response is None:
            return False

        logging.info("Reglas aceptadas.")
        return True

    # -------------------------------------------------
    # MONITOR DE MERCADO (Thread 1)
    # -------------------------------------------------

    def monitor_mercado(self):
        """
        Thread productor: consulta el estado del mercado periodicamente
        y lo guarda en self.market_state protegido por lock.
        """

        logging.info("[monitor] Inicio")

        while self.running:

            try:
                estado = self.api.get("/estado")

                if estado:
                    with self.lock:
                        self.market_state = estado

                    # Detectar fin de simulacion
                    if not estado.get("simulacion_activa", True):
                        logging.info("[monitor] Simulacion finalizada por el servidor.")
                        self.running = False
                        break

            except Exception as e:
                logging.error(f"[monitor] Error: {e}")

            time.sleep(2)

        logging.info("[monitor] Cerrado")

    # -------------------------------------------------
    # CONSULTAR PORTFOLIO
    # -------------------------------------------------

    def obtener_portfolio(self) -> dict | None:

        if not self.bot_id:
            return None

        endpoint = f"/portfolio/{self.bot_id}"
        portfolio = self.api.get(endpoint)

        return portfolio

    # -------------------------------------------------
    # OBTENER ORDENES ACTIVAS
    # -------------------------------------------------

    def obtener_ordenes(self) -> list:

        ordenes = self.api.get("/ordenes")

        if isinstance(ordenes, list):
            return ordenes

        return []

    # -------------------------------------------------
    # CANCELAR ORDEN
    # -------------------------------------------------

    def cancelar_orden(self, orden_id: str):

        endpoint = f"/orden/{orden_id}"

        response = self.api.delete(endpoint)

        if response:
            logging.info(f"Orden cancelada: {orden_id}")

    # -------------------------------------------------
    # COMPRAR
    # -------------------------------------------------

    def comprar(self, ticker: str, precio: float, cantidad: int) -> dict | None:

        orden = {
            "bot_id": self.bot_id,
            "ticker": ticker,
            "tipo": "COMPRA",
            "precio": round(precio, 2),
            "cantidad": cantidad
        }

        response = self.api.post("/orden", json=orden)

        if response:
            estado_orden = response.get("estado", "?")
            orden_id = response.get("orden_id", "?")
            logging.info(f"COMPRA enviada -> {ticker} @ {precio:.2f} x{cantidad} [{estado_orden}] id={orden_id}")
            return response

        return None

    # -------------------------------------------------
    # VENDER
    # -------------------------------------------------

    def vender(self, ticker: str, precio: float, cantidad: int) -> dict | None:

        orden = {
            "bot_id": self.bot_id,
            "ticker": ticker,
            "tipo": "VENTA",
            "precio": round(precio, 2),
            "cantidad": cantidad
        }

        response = self.api.post("/orden", json=orden)

        if response:
            estado_orden = response.get("estado", "?")
            orden_id = response.get("orden_id", "?")
            logging.info(f"VENTA enviada -> {ticker} @ {precio:.2f} x{cantidad} [{estado_orden}] id={orden_id}")
            return response

        return None

    # -------------------------------------------------
    # CONTROL ORDENES ACTIVAS
    # -------------------------------------------------

    def limpiar_ordenes(self):

        ordenes = self.obtener_ordenes()

        if len(ordenes) >= 8:

            logging.warning("Demasiadas ordenes activas, limpiando...")

            for orden in ordenes:

                orden_id = orden.get("orden_id")

                if orden_id:
                    self.cancelar_orden(orden_id)
                    time.sleep(0.3)

    # -------------------------------------------------
    # ESTRATEGIA BASICA
    # -------------------------------------------------

    def estrategia_basica(self):
        """
        Estrategia para la EP y base para la EF.

        Logica:
        - Elige el ticker mas barato disponible.
        - Si no tenemos acciones: comprar 1 accion cruzando el spread
          (precio * 1.01) para garantizar ejecucion contra SYSTEM.
        - Si ya tenemos acciones: vender a precio * 1.01 para realizar
          ganancia.

        IMPORTANTE: comprar a precio * 1.01 (sobre el mercado) garantiza
        que la orden cruza el spread del market maker SYSTEM y se EJECUTA
        inmediatamente. Comprar bajo el precio (0.99) deja la orden ACTIVA
        sin ejecutar, lo cual NO cumple el requisito de la EP.
        """

        with self.lock:
            estado = self.market_state.copy()

        if not estado:
            return

        precios = estado.get("precios", {})

        if not precios:
            return

        # Elegir el ticker mas barato (minimiza capital comprometido)
        ticker = min(precios, key=lambda t: precios[t])
        precio_actual = precios[ticker]

        if precio_actual <= 0:
            return

        # Consultar portfolio
        portfolio = self.obtener_portfolio()

        if portfolio is None:
            return

        capital = portfolio.get("capital", 0)
        activos = portfolio.get("activos", {})
        cantidad_actual = activos.get(ticker, 0)

        # -----------------------------------------
        # Si no tenemos acciones -> COMPRAR cruzando el spread
        # -----------------------------------------
        if cantidad_actual == 0:
            precio_compra = round(precio_actual * 1.01, 2)
            costo_estimado = precio_compra * 1.005  # incluir comision 0.5%

            if capital > costo_estimado + 5:  # margen para costos de requests
                response = self.comprar(ticker, precio_compra, 1)

                if response and response.get("estado") == "EJECUTADA":
                    self.orden_ejecutada = True
                    logging.info(">>> Orden EJECUTADA exitosamente. Requisito EP cumplido.")

        # -----------------------------------------
        # Si tenemos acciones -> VENDER para realizar ganancia
        # -----------------------------------------
        elif cantidad_actual > 0:
            precio_venta = round(precio_actual * 1.01, 2)
            self.vender(ticker, precio_venta, 1)

    # -------------------------------------------------
    # LOOP PRINCIPAL DE TRADING (Thread 2)
    # -------------------------------------------------

    def trading_loop(self):
        """
        Thread consumidor: lee el estado del mercado y ejecuta la estrategia.
        """

        logging.info("[trading] Inicio - esperando datos del mercado...")

        # Esperar hasta que el monitor obtenga el primer estado
        for _ in range(30):
            if not self.running:
                return
            with self.lock:
                tiene_datos = bool(self.market_state)
            if tiene_datos:
                break
            time.sleep(0.5)
        else:
            logging.error("[trading] Timeout esperando estado inicial.")
            return

        logging.info("[trading] Datos recibidos, ejecutando estrategia...")

        while self.running:

            try:

                # Limpiar ordenes si hay muchas
                self.limpiar_ordenes()

                # Ejecutar estrategia
                self.estrategia_basica()

            except Exception as e:
                logging.error(f"[trading] Error: {e}")

            time.sleep(5)

        logging.info("[trading] Cerrado")
