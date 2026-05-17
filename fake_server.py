# fake_server.py

from flask import Flask, request, jsonify

app = Flask(__name__)

# -------------------------------------------------
# DATOS SIMULADOS
# -------------------------------------------------

BOT_ID = "bot-123"
API_KEY = "abc123"

capital = 10000

activos = {
    "AAPL": 0,
    "MSFT": 0
}

ordenes_activas = []

precios = {
    "AAPL": 175.5,
    "MSFT": 330.2
}

contador_ordenes = 1

# -------------------------------------------------
# AUTENTICAR
# -------------------------------------------------

@app.route("/autenticar", methods=["POST"])
def autenticar():

    return jsonify({
        "bot_id": BOT_ID,
        "api_key": API_KEY,
        "capital_inicial": 10000,
        "mensaje": "Autenticación exitosa"
    })

# -------------------------------------------------
# ACEPTAR REGLAS
# -------------------------------------------------

@app.route("/aceptar_reglas", methods=["POST"])
def aceptar_reglas():

    return jsonify({
        "mensaje": "Reglas aceptadas"
    })

# -------------------------------------------------
# ESTADO DEL MERCADO
# -------------------------------------------------

@app.route("/estado", methods=["GET"])
def estado():

    return jsonify({
        "simulacion_activa": True,
        "tiempo_restante": 999,
        "precios": precios
    })

# -------------------------------------------------
# PORTFOLIO
# -------------------------------------------------

@app.route("/portfolio/<bot_id>", methods=["GET"])
def portfolio(bot_id):

    patrimonio = capital

    for ticker, cantidad in activos.items():

        patrimonio += cantidad * precios[ticker]

    return jsonify({
        "capital": capital,
        "activos": activos,
        "patrimonio": patrimonio,
        "comisiones_pagadas": 0
    })

# -------------------------------------------------
# ORDENES ACTIVAS
# -------------------------------------------------

@app.route("/ordenes", methods=["GET"])
def obtener_ordenes():

    return jsonify(ordenes_activas)

# -------------------------------------------------
# CREAR ORDEN
# -------------------------------------------------

@app.route("/orden", methods=["POST"])
def crear_orden():

    global contador_ordenes
    global capital

    data = request.json

    ticker = data["ticker"]
    tipo = data["tipo"]
    precio = data["precio"]
    cantidad = data["cantidad"]

    orden_id = f"ord-{contador_ordenes}"

    contador_ordenes += 1

    # -----------------------------------------
    # COMPRA
    # -----------------------------------------

    if tipo == "COMPRA":

        costo = precio * cantidad

        if capital >= costo:

            capital -= costo

            activos[ticker] += cantidad

    # -----------------------------------------
    # VENTA
    # -----------------------------------------

    elif tipo == "VENTA":

        if activos[ticker] >= cantidad:

            capital += precio * cantidad

            activos[ticker] -= cantidad

    orden = {
        "orden_id": orden_id,
        "ticker": ticker,
        "tipo": tipo,
        "precio": precio,
        "cantidad": cantidad
    }

    ordenes_activas.append(orden)

    return jsonify({
        "orden_id": orden_id,
        "estado": "ACTIVA"
    })

# -------------------------------------------------
# CANCELAR ORDEN
# -------------------------------------------------

@app.route("/orden/<orden_id>", methods=["DELETE"])
def cancelar_orden(orden_id):

    global ordenes_activas

    ordenes_activas = [
        o for o in ordenes_activas
        if o["orden_id"] != orden_id
    ]

    return jsonify({
        "orden_id": orden_id,
        "estado": "CANCELADA"
    })

# -------------------------------------------------

if __name__ == "__main__":

    app.run(port=5000)