# main.py

import sys
import time
import threading
import logging

from trader import TradingBot


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)


def main():

    if len(sys.argv) != 3:

        print("Uso: python main.py <nombre_grupo> <url_mercado>")
        sys.exit(1)

    nombre_grupo = sys.argv[1]
    base_url = sys.argv[2]

    logging.info(f"Iniciando bot '{nombre_grupo}' contra {base_url}")

    bot = TradingBot(nombre_grupo, base_url)

    # -----------------------------------------
    # AUTENTICAR
    # -----------------------------------------

    if not bot.autenticar():

        logging.error("No se pudo autenticar.")
        sys.exit(1)

    # -----------------------------------------
    # ACEPTAR REGLAS
    # -----------------------------------------

    if not bot.aceptar_reglas():

        logging.error("No se pudieron aceptar las reglas.")
        sys.exit(1)

    # -----------------------------------------
    # THREADS
    # -----------------------------------------

    monitor_thread = threading.Thread(
        target=bot.monitor_mercado,
        name="MonitorMercado",
        daemon=True
    )

    trading_thread = threading.Thread(
        target=bot.trading_loop,
        name="TradingLoop",
        daemon=True
    )

    monitor_thread.start()
    trading_thread.start()

    logging.info(f"Bot iniciado con 2 threads: {monitor_thread.name}, {trading_thread.name}")

    # -----------------------------------------
    # LOOP PRINCIPAL
    # -----------------------------------------

    try:

        while bot.running:
            time.sleep(1)

    except KeyboardInterrupt:

        logging.warning("Bot detenido manualmente (Ctrl+C).")

    finally:

        bot.running = False

        # Esperar a que los threads terminen
        monitor_thread.join(timeout=5)
        trading_thread.join(timeout=5)

        # Resumen final
        portfolio = bot.obtener_portfolio()

        if portfolio:
            logging.info("========== RESUMEN FINAL ==========")
            logging.info(f"  Capital:     {portfolio.get('capital', '?')}")
            logging.info(f"  Patrimonio:  {portfolio.get('patrimonio', '?')}")
            logging.info(f"  Activos:     {portfolio.get('activos', {})}")
            logging.info(f"  Comisiones:  {portfolio.get('comisiones_pagadas', '?')}")
            logging.info("====================================")

        logging.info("Bot finalizado.")


if __name__ == "__main__":
    main()