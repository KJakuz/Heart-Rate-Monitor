
from max30102 import MAX30102
from . import hrcalc
import threading
import time
import numpy as np


# HRV States
HRV_IDLE = 'idle'
HRV_COLLECTING = 'collecting'
HRV_READY = 'ready'

# Configuration
HRV_DURATION = 60
HRV_MIN_STABLE_TIME = 2
FINGER_DETECTION_THRESHOLD = 50000


class HeartRateMonitor(object):
    """
    A class that encapsulates the max30102 device into a thread
    """

    LOOP_TIME = 0.01

    def __init__(self):
        self.bpm = 0
        self.spo = 0
        
        # HRV state machine
        self.hrv_state = HRV_IDLE
        self.hrv_buffer_ir = []
        self.hrv_start_time = None
        self.hrv_results = None
        
        self.ir_data = []
        self.red_data = []
        
        # Stability tracking
        self._stable_start_time = None
        self._last_bpm = 0

    def run_sensor(self):
        sensor = MAX30102()
        self.ir_data = []
        self.red_data = []
        bpms = []

        # run until told to stop
        while not self._thread.stopped:
            # check if any data is available
            num_bytes = sensor.get_data_present()
            if num_bytes > 0:
                # grab all the data and stash it into arrays
                while num_bytes > 0:
                    red, ir = sensor.read_fifo()
                    
                    self.latest_ir_value = ir
                    
                    num_bytes -= 1
                    self.ir_data.append(ir)
                    self.red_data.append(red)

                    # HRV data into separate buffer
                    if self.hrv_state == HRV_COLLECTING:
                        self.hrv_buffer_ir.append(ir)

                while len(self.ir_data) > 100:
                    self.ir_data.pop(0)
                    self.red_data.pop(0)

                if len(self.ir_data) == 100:
                    bpm, valid_bpm, spo2, valid_spo2 = hrcalc.calc_hr_and_spo2(self.ir_data, self.red_data)
                    if(valid_spo2):
                        self.spo = spo2
                    else:
                        self.spo = 0
                    if valid_bpm:
                        bpms.append(bpm)
                        while len(bpms) > 4:
                            bpms.pop(0)
                        self.bpm = np.mean(bpms)
                        if (np.mean(self.ir_data) < FINGER_DETECTION_THRESHOLD and np.mean(self.red_data) < FINGER_DETECTION_THRESHOLD):
                            self.bpm = 0


                # HRV state machine
                self._update_hrv_state()

            time.sleep(self.LOOP_TIME)

        sensor.shutdown()

    def _update_hrv_state(self):
        """Update HRV state machine based on current conditions."""
        finger_detected = self.bpm > 0
        
        if self.hrv_state == HRV_IDLE:
            if finger_detected:
                if self._stable_start_time is None:
                    self._stable_start_time = time.time()
                    self._last_bpm = self.bpm
                else:
                    # Check if BPM is stable (within 10%)
                    if abs(self.bpm - self._last_bpm) < self._last_bpm * 0.1:
                        stable_duration = time.time() - self._stable_start_time
                        if stable_duration >= HRV_MIN_STABLE_TIME:
                            # Start HRV collection
                            self.hrv_state = HRV_COLLECTING
                            self.hrv_buffer_ir = []
                            self.hrv_start_time = time.time()
                    else:
                        self._stable_start_time = time.time()
                        self._last_bpm = self.bpm
            else:
                self._stable_start_time = None
                
        elif self.hrv_state == HRV_COLLECTING:
            if not finger_detected:
                self.hrv_state = HRV_IDLE
                self.hrv_buffer_ir = []
                self._stable_start_time = None
            else:
                elapsed = time.time() - self.hrv_start_time
                if elapsed >= HRV_DURATION:
                    self._calculate_hrv()
                    
        elif self.hrv_state == HRV_READY:
            pass  # Wait for acknowledge_hrv()

    def _calculate_hrv(self):
        """Calculate HRV from collected buffer."""
        self.hrv_results = hrcalc.calc_hrv_from_buffer(self.hrv_buffer_ir)
        
        if self.hrv_results and self.hrv_results['valid']:
            self.hrv_state = HRV_READY
        else:
            self.hrv_state = HRV_IDLE
            self._stable_start_time = None

    def acknowledge_hrv(self):
        """Acknowledge HRV results and reset to idle state."""
        self.hrv_state = HRV_IDLE
        self.hrv_results = None
        self.hrv_buffer_ir = []
        self._stable_start_time = None

    def get_hrv_progress(self):
        """Get HRV collection progress."""
        if self.hrv_state != HRV_COLLECTING or not self.hrv_start_time:
            return (0, HRV_DURATION, 0)
        
        elapsed = time.time() - self.hrv_start_time
        percentage = min((elapsed / HRV_DURATION) * 100, 100)
        return (elapsed, HRV_DURATION, percentage)

    def start_sensor(self):
        self._thread = threading.Thread(target=self.run_sensor)
        self._thread.stopped = False
        self._thread.start()

    def stop_sensor(self, timeout=2.0):
        self._thread.stopped = True
        self.bpm = 0
        self._thread.join(timeout)