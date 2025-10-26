import time
from machine import Pin
from machine import SPI
from math import ceil, sqrt
from fonts import asc2_0806


class TimeoutError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        
class Color():
    BLACK = 0x00
    WHITE = 0xff
    
class Rotate():
    ROTATE_0 = 0
    ROTATE_90 = 1
    ROTATE_180 = 2
    ROTATE_270 = 3

class Screen():
    def __init__(self, width=128, height=296):
        self.width = width
        self.height = height
        self.width_bytes = ceil(width / 8)
        self.height_bytes = height
        
    def __repr__(self):
        return f"Screen: {self.width}x{self.height}"

class Paint():
    def __init__(self, screen=Screen(), rotate=Rotate.ROTATE_90, bg_color=Color.WHITE):
        self.screen = screen
        self.img = bytearray(self.screen.width_bytes * self.screen.height_bytes)
        self.rotate = rotate
        self.bg_color = bg_color
        
        if self.rotate == Rotate.ROTATE_0 or self.rotate == Rotate.ROTATE_180:
            self.width = self.screen.width
            self.height = self.screen.height
        else:
            self.width = self.screen.height
            self.height = self.screen.width
        self.clear(bg_color)
            
    def clear(self, color):
        self.bg_color = color
        # Заповнюємо весь буфер кольором фону
        fill_value = 0xFF if color == Color.WHITE else 0x00
        for i in range(len(self.img)):
            self.img[i] = fill_value
    
    def _convert_coor(self, x_pos, y_pos):
        if self.rotate == Rotate.ROTATE_0:
            x = x_pos
            y = y_pos
        elif self.rotate == Rotate.ROTATE_90:
            x = self.screen.width - y_pos - 1
            y = x_pos
        elif self.rotate == Rotate.ROTATE_180:
            x = self.screen.width - x_pos - 1
            y = self.screen.height - y_pos - 1
        else:  # ROTATE_270
            x = y_pos
            y = self.screen.height - x_pos - 1
            
        return x, y
    
    def draw_point(self, x_pos, y_pos, color):
        x, y = self._convert_coor(x_pos, y_pos)
        if x >= self.screen.width or y >= self.screen.height or x < 0 or y < 0:
            return
        
        addr = x // 8 + y * self.screen.width_bytes
        bit_position = x % 8
        
        if color == Color.BLACK:
            # Встановлюємо біт в 0 для чорного
            self.img[addr] &= ~(0x80 >> bit_position)
        else:
            # Встановлюємо біт в 1 для білого
            self.img[addr] |= (0x80 >> bit_position)
            
    def draw_line(self, x_start, y_start, x_end, y_end, color=Color.BLACK):
        dx = x_end - x_start
        dy = y_end - y_start
        points = []
        
        if dx == 0 and dy == 0:
            self.draw_point(x_start, y_start, color)
            return
            
        if abs(dx) > abs(dy):
            steps = abs(dx)
            x_inc = 1 if dx > 0 else -1
            y_inc = dy / abs(dx) if dx != 0 else 0
            for i in range(steps + 1):
                x = x_start + i * x_inc
                y = y_start + round(i * y_inc)
                points.append((x, y))
        else:
            steps = abs(dy)
            y_inc = 1 if dy > 0 else -1
            x_inc = dx / abs(dy) if dy != 0 else 0
            for i in range(steps + 1):
                y = y_start + i * y_inc
                x = x_start + round(i * x_inc)
                points.append((x, y))
                
        for x, y in points:
            self.draw_point(x, y, color)
            
    def draw_rectangle(self, x_start, y_start, x_end, y_end, color=Color.BLACK):
        self.draw_line(x_start, y_start, x_end, y_start, color)
        self.draw_line(x_start, y_start, x_start, y_end, color)
        self.draw_line(x_start, y_end, x_end, y_end, color)
        self.draw_line(x_end, y_start, x_end, y_end, color)

    def draw_circle(self, x_center, y_center, radius, color=Color.BLACK):
        for x in range(x_center - radius, x_center + radius + 1):
            y = y_center + int(sqrt(radius ** 2 - (x - x_center) ** 2))
            self.draw_point(x, y, color)
            y = y_center - int(sqrt(radius ** 2 - (x - x_center) ** 2))
            self.draw_point(x, y, color)
            
    def show_char(self, char, x_start, y_start, font=asc2_0806, font_size=(6, 8), multiplier=1, color=Color.BLACK):
        char_idx = ord(char) - 32
        if char_idx < 0 or char_idx >= len(font):
            return
            
        if multiplier == 1:
            for x_offset in range(font_size[0]):
                tmp = font[char_idx][x_offset]
                for y_offset in range(font_size[1]):
                    if tmp & (1 << y_offset):
                        self.draw_point(x_start + x_offset, y_start + y_offset, color)
        else:
            for x_offset in range(font_size[0]):
                tmp = font[char_idx][x_offset]
                for y_offset in range(font_size[1]):
                    if tmp & (1 << y_offset):
                        for mx in range(multiplier):
                            for my in range(multiplier):
                                self.draw_point(x_start + x_offset * multiplier + mx, 
                                              y_start + y_offset * multiplier + my, color)
                
    def show_string(self, string, x_start, y_start, font=asc2_0806, font_size=(6, 8), multiplier=1, color=Color.BLACK):
        for idx, char in enumerate(string):
            self.show_char(char, x_start + idx * font_size[0] * multiplier, y_start, font, font_size, multiplier, color)


class SSD1680():
    def __init__(self, spi, dc, busy, cs, res):
        self.spi = spi
        self.dc = dc
        self.busy = busy
        self.cs = cs
        self.res = res
        self.screen = Screen()
        self.paint = Paint(self.screen, rotate=Rotate.ROTATE_0, bg_color=Color.WHITE)  # Змінив на ROTATE_0 для простоти
        
        # Ініціалізація пінів
        self.dc.init(Pin.OUT)
        self.busy.init(Pin.IN)
        self.cs.init(Pin.OUT)
        self.res.init(Pin.OUT)
        
        self.chip_desel()
        
    def chip_sel(self):
        self.cs(0)
        
    def chip_desel(self):
        self.cs(1)
        
    def read_busy(self, info="wait busy timeout!", timeout=10):
        st = time.time()
        while self.busy.value() == 1:
            if (time.time() - st) > timeout:
                raise TimeoutError(info)
            time.sleep(0.01)
        
    def hw_rst(self):
        print("hardware resetting...")
        self.res(0)
        time.sleep(0.2)
        self.res(1)
        time.sleep(0.2)
        self.read_busy("hardware reset timeout!")
        print("hardware reset successful")
        
    def sw_rst(self):
        print("software resetting...")
        self.write_cmd(0x12)
        self.read_busy("software reset timeout!")
        print("software reset successful")
        
    def write_cmd(self, cmd):
        self.dc(0)
        self.chip_sel()
        self.spi.write(bytearray([cmd]))
        self.chip_desel()
        
    def write_data(self, data):
        self.dc(1)
        self.chip_sel()
        self.spi.write(bytearray([data]))
        self.chip_desel()
        
    def init(self):
        self.hw_rst()
        self.sw_rst()
        
        # driver output control
        self.write_cmd(0x01)
        self.write_data(0x27)
        self.write_data(0x01)
        self.write_data(0x00)
        
        # data entry mode
        self.write_cmd(0x11)
        self.write_data(0x03)  # X increment, Y increment
        
        # set ram-x addr start/end pos
        self.write_cmd(0x44)
        self.write_data(0x00)
        self.write_data(0x0F)  # (128-1)/8 = 15 = 0x0F
        
        # set ram-y addr start/end pos
        self.write_cmd(0x45)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0x27)  # 296-1 = 295 = 0x0127
        self.write_data(0x01)
        
        # border waveform
        self.write_cmd(0x3C)
        self.write_data(0x05)
        
        # display update control
        self.write_cmd(0x21)
        self.write_data(0x00)
        self.write_data(0x80)
        
        # set ram-x addr cnt to 0
        self.write_cmd(0x4E)
        self.write_data(0x00)
        # set ram-y addr cnt to 0x127
        self.write_cmd(0x4F)
        self.write_data(0x00)
        self.write_data(0x00)
        
    def update_mem(self):
        print("updating the memory...")
        self.write_cmd(0x24)
        for i in range(len(self.paint.img)):
            self.write_data(self.paint.img[i])
        print("updating memory successful")
        
    def update_screen(self):
        # display update control
        self.write_cmd(0x22)
        self.write_data(0xF7)
        # master activation
        print("updating the screen...")
        self.write_cmd(0x20)
        self.read_busy("update screen timeout!")
        print("update screen successful")
        
    def update(self):
        self.update_mem()
        self.update_screen()
        
    def clear(self, color=Color.WHITE):
        self.paint.clear(color)
        
    def draw_point(self, x, y, color=Color.BLACK):
        self.paint.draw_point(x, y, color)
        
    def draw_line(self, x1, y1, x2, y2, color=Color.BLACK):
        self.paint.draw_line(x1, y1, x2, y2, color)
    
    def draw_rectangle(self, x1, y1, x2, y2, color=Color.BLACK):
        self.paint.draw_rectangle(x1, y1, x2, y2, color)
        
    def draw_circle(self, x, y, r, color=Color.BLACK):
        self.paint.draw_circle(x, y, r, color)
        
    def show_char(self, char, x, y, font=asc2_0806, font_size=(6, 8), multiplier=1, color=Color.BLACK):
        self.paint.show_char(char, x, y, font, font_size, multiplier, color)
        
    def show_string(self, text, x, y, font=asc2_0806, font_size=(6, 8), multiplier=1, color=Color.BLACK):
        self.paint.show_string(text, x, y, font, font_size, multiplier, color)
        
    def sleep(self):
        self.write_cmd(0x10)  # Enter deep sleep
        self.write_data(0x01)