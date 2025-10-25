from machine import Pin, SPI
import time
from epd2in9_fixed import SSD1680, Color

# === Ініціалізація ===
spi = SPI(2, baudrate=20000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(23))
epd = SSD1680(spi, Pin(17), Pin(4), Pin(5), Pin(16))

epd.init()
epd.clear(Color.WHITE)

print("=== ТЕСТ ВЕЛИКОГО ШРИФТУ ===")

# Функція для великих цифр (спрощена версія)
def draw_big_digit(epd, digit, x, y, color=Color.BLACK):
    """Малює велику цифру 48x96"""
    # Очищаємо область
    epd.draw_rectangle(x, y, x + 48, y + 96, Color.WHITE)
    
    if digit == '0':
        epd.draw_rectangle(x + 5, y + 5, x + 43, y + 91, color)
        epd.draw_rectangle(x + 15, y + 15, x + 33, y + 81, Color.WHITE)
    elif digit == '1':
        epd.draw_rectangle(x + 20, y + 5, x + 28, y + 91, color)
    elif digit == '2':
        # Верхня горизонтальна
        epd.draw_rectangle(x + 5, y + 5, x + 43, y + 15, color)
        # Середня горизонтальна
        epd.draw_rectangle(x + 5, y + 45, x + 43, y + 55, color)
        # Нижня горизонтальна
        epd.draw_rectangle(x + 5, y + 85, x + 43, y + 91, color)
        # Права вертикальна (верх)
        epd.draw_rectangle(x + 35, y + 15, x + 43, y + 45, color)
        # Ліва вертикальна (низ)
        epd.draw_rectangle(x + 5, y + 55, x + 13, y + 85, color)
    elif digit == '3':
        # Верхня горизонтальна
        epd.draw_rectangle(x + 5, y + 5, x + 43, y + 15, color)
        # Середня горизонтальна
        epd.draw_rectangle(x + 5, y + 45, x + 43, y + 55, color)
        # Нижня горизонтальна
        epd.draw_rectangle(x + 5, y + 85, x + 43, y + 91, color)
        # Права вертикальна
        epd.draw_rectangle(x + 35, y + 15, x + 43, y + 85, color)
    elif digit == '9':
        # Верхня горизонтальна
        epd.draw_rectangle(x + 5, y + 5, x + 43, y + 15, color)
        # Середня горизонтальна
        epd.draw_rectangle(x + 5, y + 45, x + 43, y + 55, color)
        # Нижня горизонтальна
        epd.draw_rectangle(x + 5, y + 85, x + 43, y + 91, color)
        # Ліва вертикальна (верх)
        epd.draw_rectangle(x + 5, y + 15, x + 13, y + 45, color)
        # Права вертикальна
        epd.draw_rectangle(x + 35, y + 15, x + 43, y + 85, color)

def draw_big_text(epd, text, x, y, color=Color.BLACK):
    """Малює великий текст"""
    spacing = 52
    for i, char in enumerate(text):
        if char in '0123456789':
            draw_big_digit(epd, char, x + i * spacing, y, color)

print("Малюю великі цифри...")

# Великі цифри
draw_big_text(epd, "01239", 10, 50, Color.BLACK)

# Підпис
epd.show_string("Big Font 48x96", 10, 160, multiplier=2, color=Color.BLACK)

epd.update()
print("Великий шрифт готовий!")
time.sleep(5)

epd.clear(Color.WHITE)
epd.sleep(100000)


