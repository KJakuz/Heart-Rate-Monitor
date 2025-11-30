import azure
from azure.iot.device import IoTHubDeviceClient, Message

CONNECTION_STRING = ""


class Telemetry:
    def __init__(self):
        self.client = IoTHubDeviceClient.create_from_connection_string(
            connection_string=CONNECTION_STRING)
        try:
            self.client.connect()
        except azure.iot.device.exceptions.ConnectionFailedError as e:
            print(f"Error while connecting to IoT Hub: {e}")
        except Exception as e:
            print(f"Error: {e}")

    def send_measurement(self, message: str):  # TODO: Standarized format for message?
        self.client.send_message(Message(message))
