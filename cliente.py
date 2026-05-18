import time
import random
import threading
import requests
import logging
from collections import deque


class RateLimiter:
    """
    Ventana deslizante para respetar el rate limit del servidor.
    Configurado a 55/10s (margen frente al limite real de 60/10s).
    Thread-safe.
    """

    def __init__(self, max_requests: int = 55, window: float = 10.0):
        self.max_requests = max_requests
        self.window = window
        self._timestamps: deque = deque()
        self._lock = threading.Lock()

    def acquire(self):
        while True:
            with self._lock:
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] > self.window:
                    self._timestamps.popleft()
                if len(self._timestamps) < self.max_requests:
                    self._timestamps.append(now)
                    return
                wait = self.window - (now - self._timestamps[0]) + 0.05
            time.sleep(max(wait, 0.05))


class APIClient:

    def __init__(self, base_url: str):

        self.base_url = base_url.rstrip("/")
        self.api_key = None
        self.rate_limiter = RateLimiter()

    def set_api_key(self, api_key: str):
        self.api_key = api_key

    def headers(self) -> dict:

        h = {}

        if self.api_key:
            h["X-API-Key"] = self.api_key

        return h

    # -----------------------------------------
    # REQUEST SEGURO CON REINTENTOS
    # -----------------------------------------

    def request(self, method: str, endpoint: str, max_retries: int = 3, **kwargs):
        """
        Hace un request HTTP con reintentos y backoff exponencial.

        Reintenta ante:
        - Timeout, ConnectionError (red caida o lenta)
        - HTTP 5xx (error del servidor)
        - HTTP 429 (rate limit excedido)
        - JSON malformado (error inyectado por el servidor)

        NO reintenta ante:
        - HTTP 4xx (salvo 429): error nuestro, reintentar no ayuda.

        Devuelve el JSON parseado o None si fallo definitivamente.
        """

        url = self.base_url + endpoint

        for intento in range(max_retries + 1):

            # Respetar rate limit ANTES de enviar
            self.rate_limiter.acquire()

            try:
                response = requests.request(
                    method,
                    url,
                    headers=self.headers(),
                    timeout=5,
                    **kwargs
                )

                status = response.status_code

                # 429: rate limit del servidor. Esperar y reintentar.
                if status == 429:
                    wait = self._backoff(intento, base=2.0)
                    logging.warning(f"429 rate limit en {method} {endpoint}, esperando {wait:.1f}s")
                    time.sleep(wait)
                    continue

                # 5xx: error del servidor. Reintentar.
                if status >= 500:
                    wait = self._backoff(intento)
                    logging.warning(f"{status} en {method} {endpoint}, reintento en {wait:.1f}s")
                    time.sleep(wait)
                    continue

                # 4xx: error nuestro. NO reintentar.
                if status >= 400:
                    logging.error(f"{status} en {method} {endpoint}: {response.text[:200]}")
                    return None

                # 2xx: intentar parsear JSON
                try:
                    return response.json()
                except ValueError:
                    # JSON malformado = error inyectado por servidor. Reintentar.
                    wait = self._backoff(intento)
                    logging.warning(f"JSON malformado en {method} {endpoint}, reintento en {wait:.1f}s")
                    time.sleep(wait)
                    continue

            except requests.exceptions.Timeout:
                wait = self._backoff(intento)
                logging.warning(f"Timeout en {method} {endpoint}, reintento en {wait:.1f}s")
                time.sleep(wait)
                continue

            except requests.exceptions.ConnectionError:
                wait = self._backoff(intento)
                logging.warning(f"ConnectionError en {method} {endpoint}, reintento en {wait:.1f}s")
                time.sleep(wait)
                continue

            except Exception as e:
                logging.error(f"Error inesperado en {method} {endpoint}: {e}")
                return None

        # Agotamos reintentos
        logging.error(f"FALLO DEFINITIVO en {method} {endpoint} tras {max_retries + 1} intentos")
        return None

    def _backoff(self, intento: int, base: float = 1.0) -> float:
        """Backoff exponencial con jitter."""
        return base * (2 ** intento) + random.random()

    # -----------------------------------------

    def get(self, endpoint: str):
        return self.request("GET", endpoint)

    def post(self, endpoint: str, **kwargs):
        return self.request("POST", endpoint, **kwargs)

    def delete(self, endpoint: str):
        return self.request("DELETE", endpoint)
