# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()
print("BOOT")
import network
import time
import ujson
import machine
import socket
import urequests
import gc




# -------------------------------
# wifi connect
# -------------------------------
def do_connect(ssid='PahNah', key='16011986', timeout=10):
    print(ssid, key)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    time.sleep(0.4)
    #wlan.disconnect()
    wlan.active(True)
    print(f'Connecting to {ssid}...')
    # Спроба підключення
    wlan.connect(ssid, key)
    # Очікування підключення з таймаутом
    start_time = time.time()
    while not wlan.isconnected():
        if time.time() - start_time > timeout:
            print('\nConnection failed: Timeout')
            wlan.disconnect()
            return None
        print('.', end='')
        time.sleep(1)
    print('\nSuccessfully connected!')
    print('Network config:', wlan.ifconfig())
    return wlan.ifconfig()[0]


# -------------------------------
# Читаємо налаштування з JSON
# -------------------------------
def load_settings():
    print("load settings")
    try:
        with open('settings.json') as f:
            return ujson.load(f)
    except:
        print("settings error")
        return {
            "wifi_ssid": "PahNah",
            "wifi_pass": "16011986",
            "wifi_timeout": "5",
            "repo_url": "https://raw.githubusercontent.com/Mykola1601/Micropython/main/Esp32/OTA/Clock/",
            "version_file": "version.txt",
            "ap_ssid": "ESP32_Setup",
            "ap_pass": "12345678"
        }


# -------------------------------
# Зберігаємо нові налаштування
# -------------------------------
def save_settings(new_data):
    # Прочитати поточні налаштування (якщо файл існує)
    try:
        with open('settings.json', 'r') as f:
            settings = ujson.load(f)
    except (OSError, ValueError):
        settings = {}  # якщо файлу немає або він пошкоджений

    # Оновити старі значення новими
    for key, value in new_data.items():
        settings[key] = value
    # Записати об’єднані налаштування назад
    try:
        with open('settings.json', 'w') as f:
            ujson.dump(settings, f)
        print("✅ Settings saved")
    except OSError as e:
        print("❌ Error saving settings:", e)



# -------------------------------
# Запускаємо точку доступу
# -------------------------------
def start_ap(essid="ESP32_Setup", password="12345678"):
    gc.collect()  # звільнити пам’ять перед стартом Wi-Fi
    ap = network.WLAN(network.AP_IF)
    ap.active(False)
    time.sleep(0.1)
    ap.active(True)
    time.sleep(1)  # ⚠️ дати Wi-Fi стеку повністю ініціалізуватись
    if not ap.active():
        print("❌ Не вдалося активувати AP інтерфейс!")
        return None
    ap.config(essid=essid, password=password, authmode=network.AUTH_WPA_WPA2_PSK)

    # Перевірка, що AP дійсно стартував
    cfg = ap.ifconfig()
    print("✅ AP mode started:", cfg)
    return ap


# -------------------------------
# Простий вебсервер для введення Wi-Fi
# -------------------------------
def web_config():
    s = socket.socket()
    s.bind(('0.0.0.0', 80))
    s.listen(1)
    print("Open Wi-Fi 'ESP_Setup' and go to http://192.168.4.1")

    html = """<!DOCTYPE html>
    <html><body>
    <h2>Wi-Fi Setup</h2>
    <form action="/" method="POST">
      SSID:<br><input name="ssid"><br>
      Password:<br><input name="pass" type="password"><br><br>
      <input type="submit" value="Save">
    </form></body></html>"""

    while True:
        conn, addr = s.accept()
        req = conn.recv(1024)
        req = req.decode()
        if "POST" in req:
            try:
                ssid = req.split('ssid=')[1].split('&')[0]
                password = req.split('pass=')[1].split(' ')[0]
                ssid = ssid.replace('+', ' ')
                password = password.replace('+', ' ')
                save_settings({
                    "wifi_ssid": ssid,
                    "wifi_pass": password,
                    "repo_url": "https://raw.githubusercontent.com/Mykola1601/Micropython/main/Esp32/OTA/Clock/",
                    "version_file": "version.txt"
                })
                response = "<h3>Saved! Rebooting...</h3>"
                conn.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + response)
                conn.close()
                time.sleep(10)
                machine.reset()
            except Exception as e:
                print("Error parsing:", e)
        else:
            conn.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + html)
            conn.close()

# -------------------------------
# OTA перевірка з GitHub
# -------------------------------
def ota_update(repo_url, version_file):
    try:
        print("Checking for updates from:", repo_url + version_file)
        r = urequests.get(repo_url + version_file)
        print("HTTP:", r.status_code)
        if r.status_code != 200:
            print("Cannot fetch version info — check repo_url/version_file")
            r.close()
            return
        remote_ver = r.text.strip()
        r.close()

        try:
            with open(version_file) as f:
                local_ver = f.read().strip()
        except:
            local_ver = "none"

        print("Local:", local_ver, "| Remote:", remote_ver)
        if remote_ver != local_ver:
            print("New version detected — downloading main.py ...")
            r = urequests.get(repo_url + "main.py")
            if r.status_code == 200:
                with open("main.py", "w") as f:
                    f.write(r.text)
                with open(version_file, "w") as f:
                    f.write(remote_ver)
                print("✅ Updated to version", remote_ver, "— restarting...")
                r.close()
                time.sleep(2)
                machine.reset()
            else:
                print("❌ Failed to download main.py:", r.status_code)
        else:
            print("🟢 Already up to date")
    except Exception as e:
        print("OTA error:", e)



# -------------------------------
# -------------------------------
# -------------------------------
# -------------------------------
gc.collect()
settings = load_settings()

if do_connect(settings["wifi_ssid"], settings["wifi_pass"], int(settings["wifi_timeout"])):
    print("✅ Wi-Fi connected, checking for updates...")
    ota_update(settings["repo_url"], settings["version_file"])
else:
    print("⚠️ No Wi-Fi connection, starting AP mode")
    ap = start_ap(settings["ap_ssid"], settings["ap_pass"])
    if ap:
        web_config()
    else:
        print("❌ Failed to start AP — rebooting")
        time.sleep(10)
        machine.reset()
