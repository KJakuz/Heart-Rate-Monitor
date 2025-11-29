from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.oled.device import ssd1351
from PIL import Image
import time


def main():
    # Initialize SPI connection
    serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=27)
    device = ssd1351(serial, width=128, height=128)

    try:
        print("Loading mount.png...")
        # Load the image
        img = Image.open("mount.png")
        # Resize to fit the 128x128 display
        img = img.resize((128, 128), Image.Resampling.LANCZOS)
        # Convert to RGB mode if needed
        img = img.convert(device.mode)

        print("Displaying image...")
        device.display(img)
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
