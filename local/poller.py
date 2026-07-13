import json
import logging
import requests

logger = logging.getLogger("poller")


class Poller:
    def __init__(self, server_url: str, on_signal):
        self.url = server_url.rstrip("/")
        self.on_signal = on_signal
        self._last_time = 0

    def fetch(self) -> bool:
        try:
            r = requests.get(f"{self.url}/last_signal", timeout=5)
            if r.status_code != 200:
                return False
            data = r.json()
            if data.get("status") == "no_signal":
                return False
            t = data.get("time", 0)
            if t and t != self._last_time:
                self._last_time = t
                self.on_signal(data)
                return True
        except requests.RequestException as e:
            logger.debug("Erro polling: %s", e)
        return False

    def set_last_time(self, t: int):
        self._last_time = t
