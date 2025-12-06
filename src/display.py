"""
Display module for the pulse oximeter.

Handles OLED display output using the SSD1351 controller,
including heart animation and BPM/SpO2 visualization.
"""

import math
import time
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.oled.device import ssd1351
from PIL import ImageFont

FONT_LARGE = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12
)
FONT_SMALL = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 8
)

def draw_heart(draw, cx, cy, scale, fill_color):
    """
    Draw a heart shape at the specified position.

    Args:
        draw: ImageDraw object
        cx: Center x coordinate
        cy: Center y coordinate
        scale: Size scaling factor
        fill_color: RGB tuple for fill color
    """
    points = []

    for t in range(0, 360, 5):
        angle = math.radians(t)
        x = 16 * math.sin(angle) ** 3
        y = -(13 * math.cos(angle) - 5 * math.cos(2 * angle) -
              2 * math.cos(3 * angle) - math.cos(4 * angle))

        x = cx + (x * scale / 16)
        y = cy + (y * scale / 16)
        points.append((x, y))

    draw.polygon(points, fill=fill_color, outline=fill_color)


def draw_spo2_symbol(draw, center_x, center_y, size, fill_color, text_color):
    """
    Draw the SpO2 blood oxygen symbol.

    Args:
        draw: ImageDraw object
        center_x: Center x coordinate
        center_y: Center y coordinate
        size: Size of the symbol
        fill_color: RGB tuple for fill color
        text_color: RGB tuple for text color
    """
    points = []

    tip_y = center_y - size * 1.2
    points.append((center_x, tip_y))

    for angle in range(0, 180, 10):
        rad = math.radians(angle)
        x = center_x + math.cos(rad) * size * 0.6
        y = center_y + math.sin(rad) * size * 0.6
        points.append((x, y))

    draw.polygon(points, fill=fill_color, outline=fill_color)

    text_x = center_x
    text_y = center_y - 2
    draw.text((text_x, text_y), "O₂", fill=text_color, font=FONT_LARGE)


def draw_hrv(draw, hrv_status, hrv_results):
    """
    Draw HRV status and results.
    
    Args:
        draw: ImageDraw object
        hrv_status: Current HRV state ('idle', 'collecting', 'ready')
        hrv_results: Either percentage (float) for 'collecting' or dict for 'ready'
    """
    if hrv_status == 'idle':
        draw.text((25, 100), "NO FINGER", fill=(0, 255, 0), font=FONT_LARGE)
        draw.text((28, 110), "DETECTED", fill=(0, 255, 0), font=FONT_LARGE)

    elif hrv_status == 'collecting':
        # hrv_results is a percentage number
        percentage = hrv_results if hrv_results is not None else 0
        hrv_text = f"HRV Calculations: {percentage}%"
        draw.text((15, 95), hrv_text, fill=(0, 255, 0), font=FONT_SMALL)
        
        # Draw loading bar
        bar_x = 15
        bar_y = 108
        bar_width = 98
        bar_height = 8
        
        # Draw outline
        draw.rectangle(
            [(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
            outline=(0, 255, 0),
            fill=(0, 0, 0)
        )
        
        # Draw filled portion based on progress
        if percentage > 0:
            fill_width = int((bar_width - 2) * (percentage / 100.0))
            draw.rectangle(
                [(bar_x + 1, bar_y + 1), (bar_x + 1 + fill_width, bar_y + bar_height - 1)],
                fill=(0, 255, 0)
            )

    elif hrv_status == 'ready':
        # hrv_results is a dictionary
        if isinstance(hrv_results, dict) and hrv_results.get('valid'):
            rmssd = hrv_results['rmssd']
            pnn50 = hrv_results['pnn50']
            
            # Interpret RMSSD: LOW < 20ms, MED 20-50ms, HIGH > 50ms
            if rmssd < 20:
                rmssd_level = "LOW"
                rmssd_color = (255, 0, 0)
            elif rmssd < 50:
                rmssd_level = "MED"
                rmssd_color = (255, 255, 0)
            else:
                rmssd_level = "HIGH"
                rmssd_color = (0, 255, 0)
            
            # Interpret pNN50: LOW < 3%, MED 3-20%, HIGH > 20%
            if pnn50 < 3:
                pnn_level = "LOW"
                pnn_color = (0, 0, 255)
            elif pnn50 < 20:
                pnn_level = "MED"
                pnn_color = (255, 255, 0)
            else:
                pnn_level = "HIGH"
                pnn_color = (0, 255, 0)
            
            draw.text((15, 90), f"RMSSD: {rmssd_level}", fill=rmssd_color, font=FONT_SMALL)
            draw.text((15, 100), f"{rmssd}ms", fill=(255, 255, 255), font=FONT_SMALL)
            draw.text((15, 110), f"pNN50: {pnn_level}", fill=pnn_color, font=FONT_SMALL)
            draw.text((15, 120), f"{pnn50}%", fill=(255, 255, 255), font=FONT_SMALL)

def draw_ekg(draw, data, bounds, color, finger_present=True):
    """
    Draw an EKG-like waveform.
    
    Args:
        draw: ImageDraw object
        data: List of numerical values (raw sensor data)
        bounds: Tuple (x, y, width, height) of the drawing area
        color: RGB tuple for line color
        finger_present: Whether finger is detected (controls display)
    """
    x_start, y_start, width, height = bounds
    y_center = y_start + height / 2
    
    if not finger_present:
        return
    
    if len(data) < 6:
        return
    
    # smoothing for cleaner signal
    smoothed = []
    for i in range(2, len(data) - 2):
        val = (data[i-2] + data[i-1] + data[i] + data[i+1] + data[i+2]) / 5.0
        smoothed.append(val)
        
    # Calculate derivative (inverted) to turn rapid drops into positive spikes
    derivative = []
    for i in range(len(smoothed) - 1):
        diff = smoothed[i] - smoothed[i+1]
        derivative.append(diff)

    if not derivative:
        return

    # Auto-scale logic
    data_to_plot = derivative
    min_val = min(data_to_plot)
    max_val = max(data_to_plot)
    val_range = max_val - min_val
    
    # if signal is too small, don't draw
    if val_range < 200:
        return
        
    points = []
    step_x = width / (len(data_to_plot) - 1) if len(data_to_plot) > 1 else 0
    
    for i, val in enumerate(data_to_plot):
        x = x_start + (i * step_x)
        
        norm = (val - min_val) / val_range - 0.5
        norm = max(-0.5, min(0.5, norm))
        
        y = y_center - (norm * height * 0.9)
        points.append((x, y))
        
    # Draw with thicker line for better visibility
    draw.line(points, fill=color, width=2)


class PulseDisplay:
    """Manages the OLED display for pulse oximeter readings."""

    def __init__(self):
        """Initialize the SPI connection and display device."""
        serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=27)
        self.device = ssd1351(serial, width=128, height=128)
        self.frame = 0
        self.current_bpm = 0
        self.current_spo = 0


    def update_display(self, bpm=None, spo=None, hrv_status='idle', hrv_results=None, raw_data=None):
        """
        Update display with new BPM and SpO2 values.

        Args:
            bpm: Heart rate in beats per minute
            spo: Blood oxygen saturation percentage
            hrv_status: Status of HRV collection
            hrv_results: HRV results or progress
            raw_data: Optional list of raw sensor values for EKG plot
        """
        if bpm is not None and spo is not None:
            self.current_bpm = bpm
            self.current_spo = spo
            
        # Use provided buffer or empty
        waveform = raw_data if raw_data is not None else []

        # Calculate pulsing heart scale
        beat_cycle = (self.frame % 20) / 20.0
        if beat_cycle < 0.3:
            pulse = 1.0 + (beat_cycle / 0.3) * 0.7
        else:
            pulse = 1.5 - ((beat_cycle - 0.3) / 0.7) * 0.7

        base_scale = 7
        heart_scale = base_scale * pulse

        with canvas(self.device) as draw:
            # Draw heart icon and BPM
            heart_x = 15
            heart_y = 15
            draw_heart(draw, heart_x, heart_y, heart_scale, fill_color=(0, 0, 255))

            bpm_text = f"{int(self.current_bpm)}"
            draw.text((35, 5), bpm_text, fill=(0, 0, 255), font=FONT_LARGE)
            draw.text((35, 20), "BPM", fill=(0, 0, 255), font=FONT_SMALL)

            # Draw SpO2 symbol and value
            spo_symbol_x = 75
            spo_symbol_y = 20
            draw_spo2_symbol(
                draw, spo_symbol_x, spo_symbol_y,
                size=10, fill_color=(255, 0, 0), text_color=(255, 255, 255)
            )
            spo_text = f"{round(float(self.current_spo), 2)}"
            draw.text((90, 5), spo_text, fill=(255, 0, 0), font=FONT_LARGE)
            draw.text((95, 20), "spo", fill=(255, 0, 0), font=FONT_SMALL)
            
            # Draw EKG Waveform in center (only when finger is present)
            finger_present = self.current_bpm > 0
            if waveform:
                draw_ekg(
                    draw, 
                    waveform, 
                    bounds=(14, 45, 100, 40),
                    color=(0, 255, 255),
                    finger_present=finger_present
                )

            draw_hrv(draw, hrv_status, hrv_results)


        time.sleep(0.05)
        self.frame += 1


    def test_display(self):
        """Test the display with cycling colors (for debugging only)."""
        i = self.frame
        colors = [(255, 255, 255), (255, 0, 0), (0, 255, 0), (128, 128, 128)]

        with canvas(self.device) as draw:
            draw.rectangle(
                self.device.bounding_box,
                outline=colors[i % 4],
                fill=colors[(i + 3) % 4]
            )
            draw.text((20, 40), "DISPLAY TESTING", fill=colors[(i + 2) % 4])
            draw.text((35, 50), "PROCEDURE", fill=colors[(i + 2) % 4])

        self.frame = i + 1
        time.sleep(1)

    def cleanup(self):
        """Clean up display resources."""
        self.device.cleanup()
        print("\nDisplay cleaned up")


if __name__ == "__main__":
    display = PulseDisplay()
    try:
        while True:
            display.test_display()
    except KeyboardInterrupt:
        pass
    finally:
        display.cleanup()