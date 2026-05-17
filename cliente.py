# cliente.py

import requests
import logging


class APIClient:

    def __init__(self, base_url):

        self.base_url = base_url
        self.api_key = None

    def set_api_key(self, api_key):
        self.api_key = api_key

    def headers(self):

        headers = {}

        if self.api_key:
            headers["X-API-Key"] = self.api_key

        return headers

    # -----------------------------------------
    # REQUEST SEGURO
    # -----------------------------------------

    def request(self, method, endpoint, **kwargs):

        url = self.base_url + endpoint

        try:

            response = requests.request(
                method,
                url,
                headers=self.headers(),
                timeout=5,
                **kwargs
            )

            response.raise_for_status()

            return response.json()

        except requests.exceptions.Timeout:
            logging.error("Timeout.")

        except requests.exceptions.ConnectionError:
            logging.error("Connection error.")

        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP Error: {e}")

        except ValueError:
            logging.error("JSON inválido.")

        except Exception as e:
            logging.error(f"Error inesperado: {e}")

        return None

    # -----------------------------------------

    def get(self, endpoint):
        return self.request("GET", endpoint)

    def post(self, endpoint, **kwargs):
        return self.request("POST", endpoint, **kwargs)

    def delete(self, endpoint):
        return self.request("DELETE", endpoint)