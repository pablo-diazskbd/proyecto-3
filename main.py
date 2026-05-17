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

    bot = TradingBot(nombre_grupo, base_url)

    # -----------------------------------------
    # AUTENTICAR
    # -----------------------------------------

    if not bot.autenticar():

        print("No se pudo autenticar.")
        sys.exit(1)

    # -----------------------------------------
    # ACEPTAR REGLAS
    # -----------------------------------------

    if not bot.aceptar_reglas():

        print("No se pudieron aceptar las reglas.")
        sys.exit(1)

    # -----------------------------------------
    # THREADS
    # -----------------------------------------

    monitor_thread = threading.Thread(
        target=bot.monitor_mercado,
        daemon=True
    )

    trading_thread = threading.Thread(
        target=bot.trading_loop,
        daemon=True
    )

    monitor_thread.start()
    trading_thread.start()

    logging.info("Bot iniciado correctamente.")

    # -----------------------------------------
    # LOOP PRINCIPAL
    # -----------------------------------------

    try:

        while True:
            time.sleep(1)

    except KeyboardInterrupt:

        logging.warning("Bot detenido manualmente.")

        bot.running = False


if __name__ == "__main__":
    main()