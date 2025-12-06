"""
Pulse oximeter main application.
Entry point that continuously displays BPM/SpO2 and shows HRV when ready.
"""
import time
from max30102 import HeartRateMonitor
from max30102.heartrate_monitor import HRV_COLLECTING, HRV_READY, HRV_IDLE
from display import PulseDisplay
from alarm_signals import AlarmSignals

STABLE_THRESHOLD = 10

if __name__ == "__main__":
    hrm = HeartRateMonitor()
    hrm.start_sensor()
    display = PulseDisplay()
    alarm = AlarmSignals()
    
    cached_hrv_results = None  # Stores HRV results to keep showing after calculation
    stable_readings = 0
    
    try:
        while True:
            finger_present = hrm.bpm > 0

            # Count stable readings (BPM in valid range)
            if finger_present:
                stable_readings += 1
            else:
                stable_readings = 0
    
            # Only alarm after readings are stable
            if stable_readings >= STABLE_THRESHOLD:
                if hrm.bpm < 50 or hrm.bpm > 120:
                    alarm.buzzer_on()
                    alarm.red_led_on()
                    alarm.green_led_off()
                    alarm.yellow_led_off()
                elif hrm.bpm > 90:
                    alarm.buzzer_off()
                    alarm.yellow_led_on()
                    alarm.red_led_off()
                    alarm.green_led_off()
                else:
                    alarm.buzzer_off()
                    alarm.green_led_on()
                    alarm.red_led_off()
                    alarm.yellow_led_off()
            else:
                alarm.all_off()
            
            # Clear cached results only when finger is removed
            if not finger_present:
                cached_hrv_results = None
            
            if hrm.hrv_state == HRV_READY:
                results = hrm.hrv_results
                if results and results.get('valid'):
                    cached_hrv_results = results
                    print(f"\n\nHRV Results:")
                    print(f"  RMSSD: {results['rmssd']} ms")
                    print(f"  pNN50: {results['pnn50']}%")
                    print(f"  Mean HR: {results['mean_hr']} BPM")
                hrm.acknowledge_hrv()
            
            if cached_hrv_results:
                hrv_status = 'ready'
                hrv_data = cached_hrv_results
            elif hrm.hrv_state == HRV_COLLECTING:
                hrv_status = 'collecting'
                _, _, percentage = hrm.get_hrv_progress()
                hrv_data = round(percentage, 1)
            else:
                hrv_status = 'idle'
                hrv_data = None
            
            display.update_display(
                bpm=hrm.bpm, 
                spo=hrm.spo, 
                hrv_status=hrv_status, 
                hrv_results=hrv_data,
                raw_data=hrm.ir_data,
            )
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        hrm.stop_sensor()
        display.cleanup()
        alarm.all_off()
        alarm.cleanup()