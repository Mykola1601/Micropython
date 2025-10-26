from machine import Pin, SPI, Timer
import time
from epd2in9_fixed import SSD1680, Color, Rotate
from fonts_64x96 import draw_digit

# === Ініціалізація дисплея ===
spi = SPI(2, baudrate=20000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(23))
epd = SSD1680(spi, Pin(17), Pin(4), Pin(5), Pin(16))
epd.init()
epd.paint.rotate = Rotate.ROTATE_90
epd.clear(Color.WHITE)

# === Параметри годинника ===
DIGIT_SPACING = 70
X_START = 1
Y_START = 10



draw_digit(epd, '0', 5, 5, Color.BLACK)
draw_digit(epd, '1', 75, 5, Color.BLACK)
draw_digit(epd, '2', 150, 5, Color.BLACK)
draw_digit(epd, '3', 200, 5, Color.BLACK)

epd.update()
time.sleep(4)

def draw_time():
    epd.clear(Color.WHITE)
    t = time.localtime()  # (year, month, mday, hour, min, sec, weekday, yearday)
    hour_str = f"{t[3]:02d}"  # дві цифри годин
    min_str = f"{t[4]:02d}"   # дві цифри хвилин

# Малюємо години
    draw_digit(epd, hour_str[0], X_START, Y_START, Color.BLACK)
    draw_digit(epd, hour_str[1], X_START + DIGIT_SPACING, Y_START, Color.BLACK)

    # Малюємо хвилини
    draw_digit(epd, min_str[0], X_START + 2*DIGIT_SPACING + 10, Y_START, Color.BLACK)
    draw_digit(epd, min_str[1], X_START + 3*DIGIT_SPACING + 10, Y_START, Color.BLACK)

    epd.update()

# === Запуск оновлення часу кожну хвилину ===
draw_time()  # спочатку відразу
timer = Timer(-1)
timer.init(period=60000, mode=Timer.PERIODIC, callback=lambda t: draw_time())
