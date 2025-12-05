"""
Pulse oximeter main application.

Entry point that continuously displays BPM/SpO2 and shows HRV when ready.
"""

import time
from max30102 import HeartRateMonitor
from max30102.heartrate_monitor import HRV_COLLECTING, HRV_READY
from display import PulseDisplay


if __name__ == "__main__":
    hrm = HeartRateMonitor()
    hrm.start_sensor()
    display = PulseDisplay()
    
    try:
        while True:
            # Always update display with current readings
            display.update_bpm(bpm=hrm.bpm, spo=hrm.spo)
            
            # Show HRV progress if collecting
            if hrm.hrv_state == HRV_COLLECTING:
                elapsed, total, percentage = hrm.get_hrv_progress()
                print(f"\rHRV: {percentage:.0f}%", end='')
            
            # Display HRV results when ready
            elif hrm.hrv_state == HRV_READY:
                hrv = hrm.hrv_results
                if hrv and hrv['valid']:
                    print(f"\n\nHRV Results:")
                    print(f"  RMSSD: {hrv['rmssd']} ms")
                    print(f"  pNN50: {hrv['pnn50']}%")
                    print(f"  Mean HR: {hrv['mean_hr']} BPM")
                
                # Acknowledge and go back to waiting for finger
                hrm.acknowledge_hrv()
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        hrm.stop_sensor()
        display.cleanup()