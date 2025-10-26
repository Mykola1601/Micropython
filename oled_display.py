import ssd1306
import time

class OLEDDisplay:
    def __init__(self, oled):
        self.oled = oled

    def draw_menu(self, title, items, selected):
        self.oled.fill(0)
        self.oled.text(title, 0, 0)
        rect_w = 128
        rect_h = 12
        for i, item in enumerate(items):
            y = 12 + i*rect_h
            if i == selected:
                self.oled.fill_rect(0, y-2, rect_w, rect_h, 1)
                self.oled.text(item, 2, y, 0)
            else:
                self.oled.text(item, 2, y, 1)
        self.oled.show()

    def show_message(self, lines, delay=None):
        self.oled.fill(0)
        for i, line in enumerate(lines):
            self.oled.text(line, 0, 12*i)
        self.oled.show()
        if delay:
            time.sleep(delay)
