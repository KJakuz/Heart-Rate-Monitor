"""
Heart rate and SpO2 calculation module.

Provides signal processing and calculation functions for heart rate,
blood oxygen saturation (SpO2), and heart rate variability (HRV) metrics.
"""

import numpy as np
import scipy.signal

SAMPLE_FREQ = 25    # Samples per second
BUFFER_SIZE = 100   # Sampling frequency * 4


def calc_hr_and_spo2(ir_data, red_data):
    """
    Calculate heart rate and SpO2 from PPG signals.

    By detecting peaks of PPG cycle and corresponding AC/DC
    of red/infra-red signal, the ratio for SpO2 is computed.

    Args:
        ir_data: Array of infrared LED readings
        red_data: Array of red LED readings

    Returns:
        tuple: (hr, hr_valid, spo2, spo2_valid, hrv_metrics)
    """
    # Ensure inputs are numpy arrays
    ir_data = np.array(ir_data)
    red_data = np.array(red_data)

    # Bandpass Filter (0.5Hz - 4Hz)
    # Removes DC component and high frequency noise
    sos = scipy.signal.butter(2, [0.5, 4], 'bandpass', fs=SAMPLE_FREQ, output='sos')
    ir_filtered = scipy.signal.sosfiltfilt(sos, ir_data)


    #  Peak Detection
    # distance=10 samples (0.4s) corresponds to max 150 BPM
    # prominence ensures we pick significant peaks
    peaks, _ = scipy.signal.find_peaks(ir_filtered, distance=10, prominence=100)

    # Calculate BPM
    if len(peaks) >= 2:
        # Calculate intervals between peaks in seconds
        intervals = np.diff(peaks) / SAMPLE_FREQ

        # Use median interval for stability
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

    # Calculate SpO2
    spo2 = -999
    spo2_valid = False
    hrv_metrics = {}

    if len(peaks) >= 2:
        ratios = []

        for i in range(len(peaks) - 1):
            start_idx = peaks[i]
            end_idx = peaks[i + 1]

            if end_idx - start_idx > 2:
                ir_segment = ir_data[start_idx:end_idx]
                red_segment = red_data[start_idx:end_idx]

                # Calculate AC and DC components
                ir_min = np.min(ir_segment)
                ir_max = np.max(ir_segment)
                red_min = np.min(red_segment)
                red_max = np.max(red_segment)

                ir_ac = ir_max - ir_min
                ir_dc = np.mean(ir_segment)
                red_ac = red_max - red_min
                red_dc = np.mean(red_segment)

                # Calculate ratio: R = (AC_red/DC_red) / (AC_ir/DC_ir)
                if ir_dc != 0 and red_dc != 0 and ir_ac != 0:
                    r = (red_ac / red_dc) / (ir_ac / ir_dc)
                    ratios.append(r)

        if len(ratios) > 0:
            ratio_avg = np.mean(ratios)

            # Scale ratio and apply calibration curve
            ratio_avg_scaled = ratio_avg * 100

            if 2 < ratio_avg_scaled < 184:
                # Quadratic calibration formula
                spo2 = (-45.060 * (ratio_avg_scaled ** 2) / 10000.0 +
                        30.054 * ratio_avg_scaled / 100.0 + 94.845)
                spo2_valid = True

            hrv_metrics = calc_hrv_metrics(peaks, SAMPLE_FREQ)

    return hr, hr_valid, spo2, spo2_valid, hrv_metrics


def calc_hrv_metrics(peaks, sample_freq=25):
    """
    Calculate HRV metrics from detected peaks.

    Args:
        peaks: Array of peak indices
        sample_freq: Sampling frequency in Hz

    Returns:
        dict: HRV metrics including RMSSD, pNN50, mean_hr, and validity
    """
    # Check minimum data requirement
    if len(peaks) < 3:
        return {
            'rmssd': -999,
            'pnn50': -999,
            'mean_hr': -999,
            'num_intervals': 0,
            'valid': False
        }

    # Calculate RR intervals (in milliseconds)
    rr_intervals = np.diff(peaks) / sample_freq * 1000

    # Filter outliers (intervals outside 300-2000 ms = 30-200 BPM)
    valid_mask = (rr_intervals >= 300) & (rr_intervals <= 2000)
    rr_intervals = rr_intervals[valid_mask]

    if len(rr_intervals) < 2:
        return {
            'rmssd': -999,
            'pnn50': -999,
            'mean_hr': -999,
            'num_intervals': 0,
            'valid': False
        }

    # Calculate successive differences
    successive_diffs = np.diff(rr_intervals)

    # RMSSD - Root Mean Square of Successive Differences
    rmssd = np.sqrt(np.mean(successive_diffs ** 2))

    # pNN50 - Percentage of intervals differing by > 50ms
    nn50 = np.sum(np.abs(successive_diffs) > 50)
    pnn50 = (nn50 / len(successive_diffs)) * 100 if len(successive_diffs) > 0 else 0

    # Mean heart rate
    mean_rr = np.mean(rr_intervals)
    mean_hr = 60000 / mean_rr  # 60000 ms per minute

    return {
        'rmssd': round(rmssd, 2),
        'pnn50': round(pnn50, 2),
        'mean_hr': round(mean_hr, 1),
        'num_intervals': len(rr_intervals),
        'valid': True
    }


def calc_hrv_from_buffer(ir_buffer, sample_freq=25):
    """
    Calculate HRV metrics from extended raw IR data buffer.
    
    This function processes a longer buffer (e.g., 60 seconds) for
    more accurate HRV calculation than the rolling 100-sample window.
    
    Args:
        ir_buffer: Extended array of raw IR readings
        sample_freq: Sampling frequency in Hz
    
    Returns:
        dict: HRV metrics including RMSSD, pNN50, mean_hr, and validity
    """
    if len(ir_buffer) < 750:  # Minimum ~30 seconds at 25Hz
        return {
            'rmssd': -999,
            'pnn50': -999,
            'mean_hr': -999,
            'num_intervals': 0,
            'valid': False
        }
    
    ir_data = np.array(ir_buffer)
    
    # Bandpass filter (0.5Hz - 4Hz) to isolate heartbeat signal
    sos = scipy.signal.butter(2, [0.5, 4], 'bandpass', fs=sample_freq, output='sos')
    ir_filtered = scipy.signal.sosfiltfilt(sos, ir_data)
    
    # Peak detection on full buffer
    peaks, _ = scipy.signal.find_peaks(ir_filtered, distance=10, prominence=100)
    
    # Use existing calc_hrv_metrics for the actual calculation
    return calc_hrv_metrics(peaks, sample_freq)