from machine import Pin, SPI
from epd2in9 import SSD1680, Color
from fonts_20x20 import draw_digit
import time

# === SPI ����������������а піни д��я ESP32 ===
spi = SPI(2, baudrate=2000000, polarity=0, phase=0,
          sck=Pin(18), mosi=Pin(23))
dc   = Pin(17, Pin.OUT)
busy = Pin(4, Pin.IN)
cs   = Pin(5, Pin.OUT)
res  = Pin(16, Pin.OUT)

# === І����і�����ал����за���і�� дисплея ===
epd = SSD1680(spi, dc, busy, cs, res)
epd.init()
epd.clear(Color.WHITE)

# === ���а����юєм��������� тес���ову к����р������ин������� ===
p = epd.paint
p.clear(Color.WHITE)

# Вел���ке �������ло
for y in range(50, 200):
    for x in range(40, 180):
        dx = x - 130
        dy = y - 90
        if dx*dx + dy*dy < 40*40:
            p.draw_point(x, y, Color.BLACK)

# ��ек�����������
p.show_string("HE6d", 20, 20, multiplier=6)
p.show_string("E-PAPER", 20, 50, multiplier=2)

# === В����ід ���������� е������р�����н ===
epd.update()  # <-- з��м���������ь epd.display()

print("������ Зобр���же������ня п����������зано!")

while True:
    time.sleep(10)
    
    
    
    
    
    
    
    