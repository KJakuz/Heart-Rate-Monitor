# -*-coding:utf-8
import numpy as np
import scipy.signal

# 25 samples per second (in algorithm.h)
SAMPLE_FREQ = 25
# sampling frequency * 4 (in algorithm.h)
BUFFER_SIZE = 100


def calc_hr_and_spo2(ir_data, red_data):
    """
    By detecting  peaks of PPG cycle and corresponding AC/DC
    of red/infra-red signal, the an_ratio for the SPO2 is computed.
    """
    
    # Ensure inputs are numpy arrays
    ir_data = np.array(ir_data)
    red_data = np.array(red_data)

    # 1. Bandpass Filter (0.5Hz - 4Hz) to remove DC and high freq noise
    # Butterworth filter, 2nd order
    sos = scipy.signal.butter(2, [0.5, 4], 'bandpass', fs=SAMPLE_FREQ, output='sos')
    ir_filtered = scipy.signal.sosfiltfilt(sos, ir_data)

    # 2. Peak Detection
    # distance=10 samples (0.4s) corresponds to max 150 BPM, preventing double counting
    # prominence ensures we pick significant peaks
    peaks, _ = scipy.signal.find_peaks(ir_filtered, distance=10, prominence=100)

    # 3. Calculate BPM
    if len(peaks) >= 2:
        # Calculate intervals between peaks in seconds
        intervals = np.diff(peaks) / SAMPLE_FREQ
        
        # Filter outliers (optional, but good for stability)
        # For now, just take the median interval
        median_interval = np.median(intervals)
        
        if median_interval > 0:
            hr = int(60 / median_interval)
            hr_valid = True
        else:
            hr = -999
            hr_valid = False
    else:
        hr = -999
        hr_valid = False

    # 4. Calculate SpO2
    # We use the raw data for SpO2 calculation, but guided by the peaks found in filtered data
    spo2 = -999
    spo2_valid = False
    
    if len(peaks) >= 2:
        ratios = []
        for i in range(len(peaks) - 1):
            # Define the cycle window between two peaks
            # We actually want the valley-to-valley or peak-to-peak window.
            # The original code looked for valleys. 
            # Let's try to find the AC/DC ratio around these peaks.
            
            # Simple approach: 
            # AC = max - min within the window
            # DC = mean within the window (or min, or max, depending on definition)
            # Standard definition: AC is peak-to-peak amplitude, DC is the baseline (valley)
            
            start_idx = peaks[i]
            end_idx = peaks[i+1]
            
            # Search for valley between peaks (min value in raw data)
            # Note: Raw IR data is inverted (absorption), so peaks in raw data are actually valleys in signal?
            # Wait, standard PPG: high absorption = low signal. 
            # Systole (heart beat) -> more blood -> high absorption -> low photodiode current.
            # So a heartbeat is a "valley" in raw light intensity.
            # The filter might have inverted this if we didn't handle it.
            # Let's look at the raw data in test_ir.
            # It seems to be around 130000.
            
            # Let's assume the standard AC/DC extraction:
            # AC component = Max - Min in the interval
            # DC component = Mean (or Min) in the interval
            
            if end_idx - start_idx > 2:
                ir_segment = ir_data[start_idx:end_idx]
                red_segment = red_data[start_idx:end_idx]
                
                ir_min = np.min(ir_segment)
                ir_max = np.max(ir_segment)
                red_min = np.min(red_segment)
                red_max = np.max(red_segment)
                
                ir_ac = ir_max - ir_min
                # ir_dc = ir_max # Using max as DC (baseline) because signal is inverted? 
                #                # Actually, usually DC is the large constant component.
                #                # Let's use the average for DC, or the max if it's inverted.
                #                # In standard MAX30102 libs, R = (AC_red/DC_red) / (AC_ir/DC_ir)
                ir_dc = np.mean(ir_segment)
                
                red_ac = red_max - red_min
                red_dc = np.mean(red_segment)
                
                if ir_dc != 0 and red_dc != 0 and ir_ac != 0:
                    r = (red_ac / red_dc) / (ir_ac / ir_dc)
                    ratios.append(r)
        
        if len(ratios) > 0:
            ratio_avg = np.mean(ratios)
            
            # Standard calibration curve (example)
            # spo2 = 110 - 25 * R (linear approximation)
            # or the quadratic one from before
            # -45.060 * ratio_ave**2 / 10000 + 30.054 * ratio_ave / 100 + 94.845
            # The previous code used a scaled ratio (ratio * 100 or something?)
            # Previous code: ratio.append(int(((nume * 100) & 0xffffffff) / denom))
            # So R was scaled by 100.
            
            # Let's use the same quadratic formula but adjust R
            # If previous R was ~100 for SpO2=98, then R=1.0 corresponds to 100.
            
            ratio_avg_scaled = ratio_avg * 100
            
            if ratio_avg_scaled > 2 and ratio_avg_scaled < 184:
                 spo2 = -45.060 * (ratio_avg_scaled**2) / 10000.0 + 30.054 * ratio_avg_scaled / 100.0 + 94.845
                 spo2_valid = True
            
    return hr, hr_valid, spo2, spo2_valid
