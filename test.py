from machine import Pin, SPI
import time
from epd2in9_fixed import SSD1680, Color

# === Ініціалізація ===
spi = SPI(2, baudrate=20000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(23))
epd = SSD1680(spi, Pin(17), Pin(4), Pin(5), Pin(16))

epd.init()
epd.clear(Color.WHITE)

print("=== ТЕСТ ВЕЛИКОГО ШРИФТУ ===")


# Підпис
epd.show_string("Big Font 48x96", 10, 160, multiplier=2, color=Color.BLACK)

epd.update()
print("Великий шрифт готовий!")
time.sleep(5)

epd.clear(Color.WHITE)
epd.sleep(100000)