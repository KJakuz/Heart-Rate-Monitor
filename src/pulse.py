import time
from max30102 import HeartRateMonitor
from display import PulseDisplay


if __name__ == "__main__":
    hrm = HeartRateMonitor()
    hrm.start_sensor()
    display = PulseDisplay()
    try:
        while True:
            display.update_bpm(hrm.bpm, hrm.spo)
            time.sleep(0.1)
    except KeyboardInterrupt:
        hrm.stop_sensor()
        display.cleanup()