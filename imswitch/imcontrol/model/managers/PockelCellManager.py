from imswitch.imcommon.framework import Signal, SignalInterface
from imswitch.imcommon.model import initLogger
import requests

URL = "http://192.168.0.177/api/"

class PockelCellManager(SignalInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)

    def sendVoltage(self, voltage_bits):
        cmd = URL + "value"
        payload = {
            "id": "up1",
            "value": voltage_bits
        }
        headers = {
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(cmd, json=payload, headers=headers)
            response.raise_for_status()  # Raises error if the request failed (HTTP 4xx/5xx)

        except requests.exceptions.RequestException as e:
            self.__logger.error("Sending control bits failed", e)

    def sendControl(self, controlbits):
        cmd = URL+"flags"
        headers = {
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(cmd, json=controlbits, headers=headers)
            response.raise_for_status()  # Raises error if the request failed (HTTP 4xx/5xx)

        except requests.exceptions.RequestException as e:
            self.__logger.error("Sending control bits failed", e)

    def getStatus(self):
        cmd = URL+"status"
        data = 0
        try:
            response = requests.get(cmd)
            response.raise_for_status()  # raises an error if HTTP response is 4xx or 5xx

            data = response.json()

        except requests.exceptions.RequestException as e:
            self.__logger.error("Get status request failed:", e)

        return data


