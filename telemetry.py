from datetime import datetime
import azure
from azure.iot.device import IoTHubDeviceClient, Message
from pydantic import BaseModel

CONNECTION_STRING = ""


class SensorData(BaseModel):
    heart_rate: float
    oxygen: float


class TelemetryMessage(BaseModel):
    device_id: str
    timestamp: datetime
    data: SensorData

# TODO: Add support for batch messages


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

    def format_message(self, x1: float, x2: float) -> TelemetryMessage:
        """Message format can be specified as BaseModel"""
        return TelemetryMessage(
            device_id="rb1",
            timestamp=datetime.now(),
            data=SensorData(x1, x2)
        )

    def send_measurement(self, message: TelemetryMessage):
        try:
            self.client.send_message(Message(message.model_dump_json()))
        except Exception as e:
            print(e)

    def close_connection(self):
        self.client.disconnect()
