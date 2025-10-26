# menu_system_dynamic.py
from machine import Pin, SoftI2C
import ssd1306
import time
import sys, select
import json
import os
import aht20_bmp280

# --- SETTINGS FILE ---
SETTINGS_FILE = "settings.json"

def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print("Save error:", e)

def load_settings():
    if SETTINGS_FILE in os.listdir():
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print("Load error:", e)
    return {}

# --- OLED setup ---
i2c = SoftI2C(scl=Pin(27), sda=Pin(26), freq=8_000_000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# === MENU CLASSES ===

class MenuItem:
    def __init__(self, label, action=None, next_page=None, go_back=False):
        self.label = label
        self.action = action
        self.next_page = next_page
        self.go_back = go_back

    def trigger(self, menu_system=None):
        if self.action:
            # виклик з menu_system як аргумент
            self.action(menu_system)
        if self.next_page:
            return self.next_page
        if self.go_back and menu_system:
            menu_system.go_back()
        return None

class OptionMenuPage(MenuItem):
    def __init__(self, title, options):
        super().__init__(title)
        self.title = title
        self.items = [MenuItem(opt) for opt in options]
        self.selected = 0
        self.selected_value = None

    def draw(self, oled):
        oled.fill(0)
        oled.text(self.title, 0, 0)
        rect_h = 12
        for i, item in enumerate(self.items):
            y = 12 + i*rect_h
            if i == self.selected:
                oled.fill_rect(0, y-1, 128, rect_h, 1)
                oled.text(item.label, 2, y, 0)
            else:
                oled.text(item.label, 2, y, 1)
        oled.show()

    def move_up(self):
        if self.selected > 0:
            self.selected -= 1

    def move_down(self):
        if self.selected < len(self.items) - 1:
            self.selected += 1

    def trigger_selected(self, menu_system=None):
        self.selected_value = self.items[self.selected].label
        print(f"{self.title} selected: {self.selected_value}")

        # збереження у JSON
        settings = load_settings()
        settings[self.title] = self.selected_value
        save_settings(settings)

        # коротке підтвердження на OLED
        oled.fill(0)
        oled.text("Saved:", 0, 0)
        oled.text(str(self.selected_value), 0, 20)
        oled.text("Returning...", 0, 50)
        oled.show()
        time.sleep(1)

        if menu_system:
            menu_system.refresh_settings_labels()
            menu_system.go_back()

class MenuPage:
    def __init__(self, title, items=None):
        self.title = title
        self.items = items or []
        self.selected = 0

    def add_item(self, item):
        self.items.append(item)

    def draw(self, oled):
        oled.fill(0)
        oled.text(self.title, 0, 0)
        rect_h = 12
        for i, item in enumerate(self.items):
            y = 12 + i*rect_h
            if i == self.selected:
                oled.fill_rect(0, y-2, 128, rect_h, 1)
                oled.text(item.label, 2, y, 0)
            else:
                oled.text(item.label, 2, y, 1)
        oled.show()

    def move_up(self):
        if self.selected > 0:
            self.selected -= 1

    def move_down(self):
        if self.selected < len(self.items)-1:
            self.selected += 1

    def get_selected_item(self):
        return self.items[self.selected] if self.items else None

# === MENU SYSTEM ===

class MenuSystem:
    def __init__(self, oled):
        self.oled = oled
        self.current_page = None
        self.page_stack = []

    def set_start_page(self, page):
        self.current_page = page
        self.page_stack = [page]
        self.current_page.draw(self.oled)

    def go_back(self):
        if len(self.page_stack) > 1:
            prev = self.page_stack[-2]
            self.page_stack.pop()
            self.current_page = prev
            prev.draw(self.oled)

    def handle_command(self, cmd):
        cmd = cmd.strip().lower()
        if not self.current_page:
            return

        if cmd in ("u","up"):
            if hasattr(self.current_page,"move_up"):
                self.current_page.move_up()
        elif cmd in ("d","down"):
            if hasattr(self.current_page,"move_down"):
                self.current_page.move_down()
        elif cmd in ("s","select"):
            if isinstance(self.current_page, OptionMenuPage):
                self.current_page.trigger_selected(menu_system=self)
            else:
                item = self.current_page.get_selected_item()
                if not item:
                    return
                next_page = item.trigger(menu_system=self)
                if next_page:
                    self.page_stack.append(next_page)
                    self.current_page = next_page
                    next_page.draw(self.oled)
        elif cmd in ("b","back"):
            self.go_back()
        elif cmd in ("q","quit"):
            oled.fill(0)
            oled.text("Goodbye!", 20,28)
            oled.show()
            raise SystemExit
        self.current_page.draw(self.oled)

    def refresh_settings_labels(self):
        settings = load_settings()
        for item in settings_menu.items:
            if "Mode" in item.label:
                item.label = f"Mode: {settings.get('Mode','?')}"
            elif "Input Num" in item.label:
                item.label = f"Input Num: {settings.get('Input Number','?')}"

# === FUNCTIONS ===

def show_message(menu_system=None, msg=""):
    oled.fill(0)
    oled.text("Selected:",0,0)
    oled.text(msg,0,20)
    oled.text("(Enter)",0,50)
    oled.show()
    input()

def show_sensor_data(menu_system=None):
    oled.fill(0)
    oled.text("Sensors Live",0,0)
    oled.text("q>quit",0,54)
    oled.show()
    time.sleep(1)
    poll = select.poll()
    poll.register(sys.stdin, select.POLLIN)
    while True:
        try:
            t = aht20_bmp280.temp()
            h = aht20_bmp280.humidity()
            p = aht20_bmp280.press()
            alt = aht20_bmp280.height()
        except:
            oled.fill(0)
            oled.text("Sensor Error!",0,0)
            oled.show()
            time.sleep(1)
            return
        oled.fill(0)
        oled.text(f"T:{t}",0,0)
        oled.text(f"H:{h}",0,12)
        oled.text(f"P:{p}",0,24)
        oled.text(f"Alt:{alt}",0,36)
        oled.text("q>quit",0,50)
        oled.show()
        if poll.poll(1000):
            cmd = sys.stdin.readline().strip().lower()
            if cmd=="q":
                break

def input_number(menu_system=None):
    settings = load_settings()
    prev = settings.get("Input Number","")
    oled.fill(0)
    oled.text("Enter number:",0,0)
    if prev:
        oled.text(f"Last: {prev}",0,20)
    oled.show()
    while True:
        try:
            val = float(input("Enter a number: "))
            print("You entered:",val)
            settings["Input Number"] = val
            save_settings(settings)
            oled.fill(0)
            oled.text("Saved!",0,0)
            oled.show()
            time.sleep(1)
            if menu_system:
                menu_system.refresh_settings_labels()
            break
        except ValueError:
            oled.fill(0)
            oled.text("Invalid!",0,0)
            oled.show()
            time.sleep(1)

# === MENU STRUCTURE ===

main_menu = MenuPage("Main Menu")
settings_menu = MenuPage("Settings")
food_menu = MenuPage("Food")
drinks_menu = MenuPage("Drinks")
ticcs_menu = MenuPage("TICCS")

saved = load_settings()

# Food
food_menu.add_item(MenuItem("Soup", action=lambda ms=None: show_message(ms,"Soup")))
food_menu.add_item(MenuItem("Dumplings", action=lambda ms=None: show_message(ms,"Dumplings")))
food_menu.add_item(MenuItem("Pizza", action=lambda ms=None: show_message(ms,"Pizza")))
food_menu.add_item(MenuItem("Back", go_back=True))

# Drinks
drinks_menu.add_item(MenuItem("Coffee", action=lambda ms=None: show_message(ms,"Coffee")))
drinks_menu.add_item(MenuItem("Tea", action=lambda ms=None: show_message(ms,"Tea")))
drinks_menu.add_item(MenuItem("Juice", action=lambda ms=None: show_message(ms,"Juice")))
drinks_menu.add_item(MenuItem("Back", go_back=True))

# TICCS
ticcs_menu.add_item(MenuItem("Zones", action=lambda ms=None: show_message(ms,"Zones")))
ticcs_menu.add_item(MenuItem("Sectors", action=lambda ms=None: show_message(ms,"Sectors")))
ticcs_menu.add_item(MenuItem("Routes", action=lambda ms=None: show_message(ms,"Routes")))
ticcs_menu.add_item(MenuItem("Back", go_back=True))

# Settings
mode_val = saved.get("Mode","?")
num_val = saved.get("Input Number","?")
mode_page = OptionMenuPage("Mode",["A","B","C"])

settings_menu.add_item(MenuItem("Sensors", action=show_sensor_data))
settings_menu.add_item(MenuItem(f"Input Num:{num_val}", action=lambda ms=None: input_number(ms)))
settings_menu.add_item(MenuItem(f"Mode: {mode_val}", next_page=mode_page))
settings_menu.add_item(MenuItem("Back", go_back=True))

# Main
main_menu.add_item(MenuItem("Food", next_page=food_menu))
main_menu.add_item(MenuItem("Settings", next_page=settings_menu))
main_menu.add_item(MenuItem("Drinks", next_page=drinks_menu))
main_menu.add_item(MenuItem("TICCS", next_page=ticcs_menu))

# --- RUN ---
menu_system = MenuSystem(oled)
menu_system.set_start_page(main_menu)
print("Use commands: u=up, d=down, s=select, b=back, q=quit")
while True:
    cmd = input("> ")
    menu_system.handle_command(cmd)
