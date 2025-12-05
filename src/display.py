from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.oled.device import ssd1351
import time
import math
from PIL import ImageFont

font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 8)


def draw_heart(draw, cx, cy, scale, fill_color):
    points = []

    for t in range(0, 360, 5):
        angle = math.radians(t)
        x = 16 * math.sin(angle) ** 3
        y = -(13 * math.cos(angle) - 5 * math.cos(2 * angle) - 2 * math.cos(3 * angle) - math.cos(4 * angle))

        x = cx + (x * scale / 16)
        y = cy + (y * scale / 16)
        points.append((x, y))

    draw.polygon(points, fill=fill_color, outline=fill_color)

def draw_spo2_symbol(draw, center_x, center_y, size, fill_color, text_color):
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
    draw.text((text_x, text_y), "O₂", fill=text_color, font=font_large)

class PulseDisplay:
    """Manages the display"""
    def __init__(self):
        # Initialize SPI connection
        serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=27)
        self.device = ssd1351(serial, width=128, height=128)
        self.frame = 0
        self.current_bpm = 0
        self.current_spo = 0

    def update_bpm(self, bpm=None, spo=None):
        """Update display with new BPM value (call this repeatedly)"""
        if bpm is not None and spo is not None:
            self.current_bpm = bpm
            self.current_spo = spo

        # Calculate pulsing heart scale
        beat_cycle = (self.frame % 20) / 20.0
        if beat_cycle < 0.3:
            pulse = 1.0 + (beat_cycle / 0.3) * 0.7
        else:
            pulse = 1.5 - ((beat_cycle - 0.3) / 0.7) * 0.7

        base_scale = 7
        heart_scale = base_scale * pulse


        with canvas(self.device) as draw:
            # Draw BPM text
            heart_x = 15
            heart_y = 15
            draw_heart(draw, heart_x, heart_y, heart_scale, fill_color=(0, 0, 255))

            bpm_text = f"{int(self.current_bpm)}"
            draw.text((35, 5), bpm_text, fill=(0, 0, 255), font=font_large)
            draw.text((35, 20), "BPM", fill=(0, 0, 255), font=font_small)

            # Draw SPO2
            spo_symbol_x = 75
            spo_symbol_y = 20
            draw_spo2_symbol(draw, spo_symbol_x, spo_symbol_y, size = 10, fill_color=(255,0,0), text_color = (255,255,255))
            spo_text = f"{round(float(self.current_spo),2)}"
            draw.text((90, 5), spo_text, fill=(255,0,0), font=font_large)
            draw.text((95, 20), "spo", fill=(255,0,0), font=font_small)


        time.sleep(0.05)
        self.frame += 1

    #FUNCTION ONLY TO TEST
    def test_display(self):
        i = self.frame
        colors = [(255,255,255), (255,0,0), (0,255,0), (128,128,128)]
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline=colors[i%4], fill=colors[(i+3)%4])
            draw.text((20, 40), "DISPLAY TESTING", fill=colors[(i+2)%4])
            draw.text((35,50), "PROCEDURE", fill=colors[(i+2)%4])
        self.frame = i + 1
        time.sleep(1)


    def cleanup(self):
        self.device.cleanup()
        print("\nDisplay cleaned up")


if __name__ == "__main__":
    display = PulseDisplay()
    try:
        while(True):
            #display.test_display()
            display.update(bpm=75)
    except KeyboardInterrupt:
        pass
    finally:
        display.cleanup()