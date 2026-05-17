# trader.py

import time
import threading
import logging

from cliente import APIClient


class TradingBot:

    def __init__(self, nombre_grupo, base_url):

        self.nombre_grupo = nombre_grupo
        self.base_url = base_url

        self.api = APIClient(base_url)

        self.bot_id = None
        self.api_key = None

        self.running = True

        # Estado compartido
        self.market_state = {}

        self.lock = threading.Lock()

    # -------------------------------------------------
    # AUTENTICACION
    # -------------------------------------------------

    def autenticar(self):

        body = {
            "nombre": self.nombre_grupo,
            "codigo": "clave-secreta"
        }

        response = self.api.post("/autenticar", json=body)

        if response is None:
            return False

        self.bot_id = response["bot_id"]
        self.api_key = response["api_key"]

        self.api.set_api_key(self.api_key)

        logging.info("Autenticación exitosa.")
        return True

    # -------------------------------------------------
    # ACEPTAR REGLAS
    # -------------------------------------------------

    def aceptar_reglas(self):

        response = self.api.post("/aceptar_reglas")

        if response is None:
            return False

        logging.info("Reglas aceptadas.")
        return True

    # -------------------------------------------------
    # MONITOR DE MERCADO
    # -------------------------------------------------

    def monitor_mercado(self):

        while self.running:

            estado = self.api.get("/estado")

            if estado:

                with self.lock:
                    self.market_state = estado

            time.sleep(2)

    # -------------------------------------------------
    # CONSULTAR PORTFOLIO
    # -------------------------------------------------

    def obtener_portfolio(self):

        endpoint = f"/portfolio/{self.bot_id}"

        portfolio = self.api.get(endpoint)

        if portfolio:
            return portfolio

        return None

    # -------------------------------------------------
    # OBTENER ORDENES ACTIVAS
    # -------------------------------------------------

    def obtener_ordenes(self):

        ordenes = self.api.get("/ordenes")

        if ordenes:
            return ordenes

        return []

    # -------------------------------------------------
    # CANCELAR ORDEN
    # -------------------------------------------------

    def cancelar_orden(self, orden_id):

        endpoint = f"/orden/{orden_id}"

        response = self.api.delete(endpoint)

        if response:
            logging.info(f"Orden cancelada: {orden_id}")

    # -------------------------------------------------
    # COMPRAR
    # -------------------------------------------------

    def comprar(self, ticker, precio, cantidad):

        orden = {
            "bot_id": self.bot_id,
            "ticker": ticker,
            "tipo": "COMPRA",
            "precio": round(precio, 2),
            "cantidad": cantidad
        }

        response = self.api.post("/orden", json=orden)

        if response:
            logging.info(f"COMPRA enviada -> {ticker}")

    # -------------------------------------------------
    # VENDER
    # -------------------------------------------------

    def vender(self, ticker, precio, cantidad):

        orden = {
            "bot_id": self.bot_id,
            "ticker": ticker,
            "tipo": "VENTA",
            "precio": round(precio, 2),
            "cantidad": cantidad
        }

        response = self.api.post("/orden", json=orden)

        if response:
            logging.info(f"VENTA enviada -> {ticker}")

    # -------------------------------------------------
    # CONTROL ORDENES ACTIVAS
    # -------------------------------------------------

    def limpiar_ordenes(self):

        ordenes = self.obtener_ordenes()

        if len(ordenes) >= 8:

            logging.warning("Demasiadas órdenes activas.")

            for orden in ordenes:

                orden_id = orden["orden_id"]

                self.cancelar_orden(orden_id)

                time.sleep(0.5)

    # -------------------------------------------------
    # ESTRATEGIA SIMPLE
    # -------------------------------------------------

    def estrategia_basica(self):

        with self.lock:
            estado = self.market_state.copy()

        if not estado:
            return

        precios = estado.get("precios", {})

        if not precios:
            return

        ticker = list(precios.keys())[0]

        precio_actual = precios[ticker]

        # Revisar portfolio
        portfolio = self.obtener_portfolio()

        if portfolio is None:
            return

        capital = portfolio["capital"]

        activos = portfolio["activos"]

        cantidad_actual = activos.get(ticker, 0)

        # Si no tenemos acciones -> comprar
        if cantidad_actual == 0 and capital > precio_actual:

            precio_compra = precio_actual * 0.99

            self.comprar(
                ticker=ticker,
                precio=precio_compra,
                cantidad=1
            )

        # Si tenemos acciones -> vender
        else:

            precio_venta = precio_actual * 1.01

            self.vender(
                ticker=ticker,
                precio=precio_venta,
                cantidad=1
            )

    # -------------------------------------------------
    # LOOP PRINCIPAL
    # -------------------------------------------------

    def trading_loop(self):

        while self.running:

            try:

                # Evitar exceder limite de ordenes
                self.limpiar_ordenes()

                # Ejecutar estrategia
                self.estrategia_basica()

            except Exception as e:
                logging.error(f"Error en trading loop: {e}")

            time.sleep(5)