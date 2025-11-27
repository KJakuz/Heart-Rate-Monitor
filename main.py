from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.oled.device import ssd1351
import time


def main():
    # Initialize SPI connection
    serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=27)
    device = ssd1351(serial, width=128, height=128)

    try:
        print("hello world display")
        with canvas(device) as draw:
            draw.rectangle([(0, 0), (127, 127)], fill="black")
            draw.text((25, 50), "Hello", fill="cyan")
            draw.text((25, 65), "World!", fill="yellow")

        print("Display updated!")
        
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nExiting...")

    finally:
        # Properly cleanup the device
        print("Cleaning up...")
        device.cleanup()
        print("Done!")


if __name__ == "__main__":
    main()
