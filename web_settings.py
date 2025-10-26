import network
import socket
import time
import json
import machine
import _thread

SETTINGS_FILE = "settings.json"


# === Ф����НКЦІЇ ��БЕРЕЖ����ННЯ/ЗАВАНТ��ЖЕНН�� ===
def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f)
        print("✅ Settings saved.")
    except Exception as e:
        print("❌ Save error:", e)

def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

# === Wi-Fi к����і��нт��ький р��жим (STA) ===
def connect_sta(ssid, password, timeout=10):
    # вимикаємо інші інтерфейси перед підключенням
    ap = network.WLAN(network.AP_IF)
    if ap.active():
        ap.active(False)
    time.sleep(1)

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    time.sleep(1)
    wlan.connect(ssid, password)
    print(f"🔌 Connecting to {ssid} ...")

    for _ in range(timeout * 2):
        if wlan.isconnected():
            print("✅ Connected:", wlan.ifconfig())
            return True
        time.sleep(0.5)

    print("❌ Connection failed.")
    wlan.active(False)
    return False

# === ����очк�� дос��уп�� (AP) ===
def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="ESP32_Config", password="12345678")
    ip = ap.ifconfig()[0]
    print(f"�������� AP started: SSID=ESP32_Config, IP={ip}")
    return ap, ip

def stop_ap(ap):
    if ap and ap.active():
        ap.active(False)
        print("🛑 AP disabled.")

# === WEB С������ВЕР ===
def config_server(stop_event):
    ap, ip = start_ap()
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    s.settimeout(1)  # ��ер��вірка на тайм����т

    html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>ESP32 WiFi Setup</title></head>
<body>
<h2>Wi-Fi Setup</h2>
<form method="POST">
  <label>SSID:</label><br>
  <input name="ssid" required><br><br>
  <label>Password:</label><br>
  <input name="password" type="password" required><br><br>
  <input type="submit" value="Save & Connect">
</form>
</body>
</html>"""

    print(f"🌐 Open http://{ip} in your browser")

    while not stop_event["stop"]:
        try:
            cl, addr = s.accept()
        except OSError:
            continue  # т��йма��т �� просто п����реві��яємо прап��рець

        print("Client connected from", addr)
        req = cl.recv(1024).decode()
        if "POST" in req:
            body = req.split("\r\n\r\n")[1]
            params = {}
            for kv in body.split("&"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    params[k] = v.replace("+", " ")

            ssid = params.get("ssid", "")
            password = params.get("password", "")
            if ssid:
                save_settings({"ssid": ssid, "password": password})
                cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
                cl.send("<h3>✅ Saved! Rebooting...</h3>")
                cl.close()
                time.sleep(2)
                machine.reset()
                return
        else:
            cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
            cl.send(html)
            cl.close()

    # ко��и час ����ийшов ��� в��ми��аємо AP
    stop_ap(ap)
    s.close()

# === Г��ЛОВНА ЛОГ��КА ===
def main():
    settings = load_settings()
    stop_event = {"stop": False}

    # Спр��ба пі��клю��итись до Wi-Fi, якщ����� є налаштування
    connected = False
    if "ssid" in settings and settings["ssid"]:
        connected = connect_sta(settings["ssid"], settings["password"])

    # Як��о не вдал������ підкл��читись ��� запускаємо AP ����� 10 хв
    if not connected:
        print("��️ Starting AP mode for configuration (10 minutes)...")
        _thread.start_new_thread(config_server, (stop_event,))
        for i in range(600):  # 600 ��������унд = 10 хвилин
            time.sleep(1)
        stop_event["stop"] = True
        print("⌛ Configuration window closed.")
        # перезапускаєм��, щоб ���пробув��ти п����дключення знову
        machine.reset()
    else:
        print("✅ Running normal operation...")
        while True:
            print("Connected, IP:", network.WLAN(network.STA_IF).ifconfig()[0])
            time.sleep(5)

if __name__ != "__main__":
    main()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    #