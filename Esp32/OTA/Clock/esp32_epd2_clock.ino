//display epd 128x296 2.9' 68x30mm

#include <GxEPD2_BW.h>
//#include <Fonts/Picopixel.h>
#include <Fonts/FreeSansBold56pt7b.h>
//#include <Fonts/FreeSansBold12pt7b.h>
#include "GxEPD2_display_selection_new_style.h"

#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <esp_sleep.h>
#include <time.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <Update.h>


// ===================== VERSION =====================
const int CURRENT_VERSION = 2; // поточна версія прошивки
String ota_base_url = "https://raw.githubusercontent.com/Mykola1601/Micropython/main/Esp32/OTA/Clock/";


// ===================== RTC =====================
RTC_DATA_ATTR time_t rtcEpoch = 0;

// ===================== DEFAULT TIME =====================
#define DEFAULT_YEAR   2026
#define DEFAULT_MONTH  1
#define DEFAULT_DAY    1
#define DEFAULT_HOUR   12
#define DEFAULT_MINUTE 0

// ===================== WIFI STORAGE =====================
Preferences prefs;
String wifi_ssid;
String wifi_pass;

int tz_hours;
String ota_url ;
int lastSyncHour = -1;

// ===================== NTP =====================
const char* ntpServer = "pool.ntp.org";
long  gmtOffset_sec = 3600 * 2;
const int   daylightOffset_sec = 3600;

// ===================== WEB =====================
WebServer server(80);

// ===================== HTML =====================
const char PAGE[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<h2>EPD Clock setup</h2>
<form action="/save">
SSID:<br>
<input name="s"><br><br>
Password:<br>
<input name="p" type="password"><br><br>
Timezone (hours):<br>
<input name="t" type="number" value="2"><br><br>
OTA update server URL:<br>
<input name="o" style="width:100%" 
 value="https://raw.githubusercontent.com/Mykola1601/Micropython/main/Esp32/OTA/Clock/"><br><br>
<input type="submit" value="Save & Reboot">
</form>
</body>
</html>
)rawliteral";



// =======================================================
// DISPLAY STATUS (BOTTOM)
// =======================================================
void showStatus(const String& msg)
{
  display.setFont(0);
//  display.setFont(&Picopixel);
  display.setPartialWindow(0, 100, display.width(), 28);

  display.firstPage();
  do {
    display.fillRect(0, 100, display.width(), 28, GxEPD_WHITE);
    display.setCursor(0, 121);
    display.print(msg);
  } while (display.nextPage());
}

// =======================================================
// WIFI CREDS
// =======================================================
void loadWiFiCreds()
{
  prefs.begin("wifi", true);
  wifi_ssid = prefs.getString("ssid", "PahNah");
  wifi_pass = prefs.getString("pass", "16011988");
  tz_hours  = prefs.getInt("tz", 2);
  ota_url   = prefs.getString(
                "ota",
                "https://github.com/Mykola1601/Micropython/tree/main/Esp32/OTA/Clock"
              );
  prefs.end();
}



void fullRefreshTime(uint8_t h, uint8_t m)
{
  display.setFullWindow();
  display.setFont(&FreeSansBold56pt7b);
  display.setTextColor(GxEPD_BLACK);
  char buf[6];
  sprintf(buf, "%02d:%02d", h, m);
  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);

    int16_t bx, by;
    uint16_t bw, bh;
    display.getTextBounds(buf, 0, 0, &bx, &by, &bw, &bh);

    uint16_t x = (display.width() - bw) / 2 - bx;
    uint16_t y = (display.height() - bh) / 2 - by - 12;

    display.setCursor(x, y);
    display.print(buf);
  } while (display.nextPage());
//  delay(100);
}




void saveWiFiCreds(String s, String p, int tz, String ota)
{
  prefs.begin("wifi", false);
  prefs.putString("ssid", s);
  prefs.putString("pass", p);
  prefs.putInt("tz", tz);
  prefs.putString("ota", ota);
  prefs.end();
}


// =======================================================
// CONNECT WIFI (2 min)
// =======================================================
bool connectWiFi(uint32_t timeout_ms)
{
  WiFi.begin(wifi_ssid.c_str(), wifi_pass.c_str());
  uint32_t start = millis();

  while (millis() - start < timeout_ms)
  {
    if (WiFi.status() == WL_CONNECTED)
      return true;
    delay(1000);
  }
  return false;
}

// =======================================================
// AP MODE
// =======================================================
unsigned long apStartMillis = 0;
bool apMode = false;
void startAP()
{
  apMode = true;

  WiFi.mode(WIFI_AP);
  WiFi.softAP("EPD-CLOCK");

  IPAddress ip = WiFi.softAPIP();
  showStatus("Connect to WiFi 'EPD-CLOCK' go to: " + ip.toString());

  server.on("/", []() {
    server.send(200, "text/html", PAGE);
  });

  server.on("/save", []() {
    String s = server.arg("s");
    String p = server.arg("p");
    int tz   = server.arg("t").toInt();
    String o = server.arg("o");

    if (tz < -12 || tz > 14) tz = 2;
    if (o.length() < 10)
      o = "https://github.com/Mykola1601/Micropython/tree/main/Esp32/OTA/Clock";

    saveWiFiCreds(s, p, tz, o);

    server.send(200, "text/html", "Saved. Rebooting...");
    delay(1000);
    ESP.restart();
  });

  server.begin();

  apStartMillis = millis();   // <<< ВАЖЛИВО
}




// =======================================================
// DEFAULT TIME
// =======================================================
time_t makeDefaultEpoch()
{
  struct tm t{};
  t.tm_year = DEFAULT_YEAR - 1900;
  t.tm_mon  = DEFAULT_MONTH - 1;
  t.tm_mday = DEFAULT_DAY;
  t.tm_hour = DEFAULT_HOUR;
  t.tm_min  = DEFAULT_MINUTE;
  t.tm_sec  = 0;
  return mktime(&t);
}


// =======================================================
// CLOCK DRAW
// =======================================================
void showTimeCenter(uint8_t h, uint8_t m)
{
  display.setFont(&FreeSansBold56pt7b);
  const char ref[] = "88:88";
  int16_t bx, by;
  uint16_t bw, bh;
  display.getTextBounds(ref, 0, 0, &bx, &by, &bw, &bh);
  uint16_t cx = display.width() / 2;
  uint16_t cy = display.height() / 2 - 12;
  uint16_t x = cx - bw / 2 - bx;
  uint16_t y = cy - bh / 2 - by;
  uint16_t pad = 10;
  uint16_t win_x = x + bx - pad;
  uint16_t win_y = y + by - pad;
  uint16_t win_w = bw + pad * 2;
  uint16_t win_h = bh + pad * 2;
  display.setPartialWindow(win_x, win_y, win_w, win_h);
  char buf[6];
  sprintf(buf, "%02d:%02d", h, m);
  display.firstPage();
  do {
    display.fillRect(win_x, win_y, win_w, win_h, GxEPD_WHITE);
    display.setCursor(x, y);
    display.print(buf);
  } while (display.nextPage());
//    delay(100);
}





// ===================== OTA =====================
// Перевіряємо, чи існує файл OTA на сервері
bool otaAvailable(String url) {
  WiFiClientSecure client;
  client.setInsecure();  // Ігноруємо сертифікат (небезпечно для продуктиву, але для тестів ок)
  HTTPClient https;

  if (https.begin(client, url)) {
    int code = https.GET();
    https.end();
    return (code == 200);
  }
  return false;
}

bool performOTA(String url) {
  WiFiClientSecure client;
  client.setInsecure(); // HTTPS без сертифікатів
  HTTPClient https;

  if (!https.begin(client, url)) {
    return false;
  }

  int code = https.GET();
  if (code != 200) {
    https.end();
    return false;
  }

  int contentLength = https.getSize();
  WiFiClient * stream = https.getStreamPtr();

  if (!Update.begin(contentLength)) {
    https.end();
    return false;
  }

  size_t written = Update.writeStream(*stream);

  https.end();

  if (written == contentLength) {
    if (Update.end(true)) {
      return true; // успішно
    }
  }

  return false;
}

// Функція, яку можна викликати кожні xx годин
void checkForOTA() {
  if (wifi_ssid.length() && connectWiFi(20000)) {
    showStatus("Connected to WiFi");

    int nextVersion = CURRENT_VERSION + 1;
    String nextBinUrl = ota_base_url + String(nextVersion) + ".bin";

    if (otaAvailable(nextBinUrl)) {
      showStatus("OTA v" + String(nextVersion));
      if (performOTA(nextBinUrl)) {
        showStatus("OTA complete. Reboot");
        delay(2000);
        ESP.restart();
      } else {
        showStatus("OTA failed");
      }
    } else {
      showStatus("No new OTA");
        delay(3000);
      showStatus(" ");
    }

    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
  }
}



bool isNight() {
    time_t now;
    time(&now);
    struct tm tm;
    localtime_r(&now, &tm);

    // нічний режим з 22:00 до 07:00
    if (tm.tm_hour >= 22 || tm.tm_hour < 7) return true;
    return false;
}



// ====================== Синхронізація часу ======================
void syncTime() {
    if (wifi_ssid.length() && connectWiFi(20000)) {
        showStatus("Sync time...");
        configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
        struct tm tm;
        if (getLocalTime(&tm, 10000)) {
            rtcEpoch = mktime(&tm);  // зберігаємо у RTC
            showStatus("Time synced");
            delay(1000);
        } else {
            showStatus("Time sync failed");
            delay(1000);
        }
        WiFi.disconnect(true);
        WiFi.mode(WIFI_OFF);
    }
}






// =======================================================
// SETUP
// =======================================================
void setup()
{
//  saveWiFiCreds("PahNah", "16011986",2, ota_base_url);
  
  display.init(115200, true, 2, false);
  display.setRotation(1);
  display.setTextColor(GxEPD_BLACK);

  loadWiFiCreds();
  gmtOffset_sec = 3600 * tz_hours;
  
  struct tm tm;
  bool needNTP = (rtcEpoch == 0);

  if (!needNTP)
  {
    localtime_r(&rtcEpoch, &tm);
    if ((tm.tm_year + 1900) < 2026)
      needNTP = true;
  }

  if (needNTP && wifi_ssid.length())
  {
    showStatus("Connecting to: " + wifi_ssid +"  ver."+String(CURRENT_VERSION));

    if (connectWiFi(120000))
    {
      showStatus("ver" + String(CURRENT_VERSION) + " Connected to WiFi: " + wifi_ssid);
      configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
      if (getLocalTime(&tm, 10000))
        rtcEpoch = mktime(&tm);

      WiFi.disconnect(true);
      WiFi.mode(WIFI_OFF);
      return;
    }
  }

  if (needNTP)
  {
    if (rtcEpoch == 0)
      rtcEpoch = makeDefaultEpoch();
    startAP();
  }

}


// =======================================================
// LOOP
// =======================================================
void loop()
{    
 if (apMode)
{
  server.handleClient();

  // ---- перевірка таймауту AP ----
  if (millis() - apStartMillis > 10UL * 60UL * 1000UL) //10 min
  {
    showStatus("deep sleep. Press Restart");

    delay(5000);  // щоб встиг прочитати

    display.hibernate(); // e-ink в спокій
    esp_sleep_enable_timer_wakeup(3600ULL * 1000000ULL); // 1 година
    esp_deep_sleep_start();
  }

  delay(10);
  return;
}

 // ---- беремо поточний час ----
    time_t now;
    time(&now);
    struct tm tm;
    localtime_r(&now, &tm);


// ---- синхронізація часу кожні 12 годин ----
if ((tm.tm_min == 45) && (tm.tm_hour % 12 == 0) && (lastSyncHour != tm.tm_hour)) {
    syncTime();
    lastSyncHour = tm.tm_hour;
}


    
      if (isNight()) {
        // ---- Повне оновлення кожні 4 години на 30-й хвилині ----
        if ((tm.tm_min == 30) && (tm.tm_hour % 4 == 0))
        {
            fullRefreshTime(tm.tm_hour, tm.tm_min);
        }
        else
        {
            showTimeCenter(tm.tm_hour, tm.tm_min);
        }
        
        // ---- статус ----
        showStatus("Night mode");
        
        // ---- спати 60x15 секунд ----
        esp_sleep_enable_timer_wakeup(900ULL * 1000000ULL);
        esp_light_sleep_start();

        }
        
      else {
        // ---- Повне оновлення кожні 2 години на 30-й хвилині ----
        if ((tm.tm_min == 30) && (tm.tm_hour % 2 == 0))
        {
            fullRefreshTime(tm.tm_hour, tm.tm_min);
        }
        else
        {
            showTimeCenter(tm.tm_hour, tm.tm_min);
        }
    
        // ---- спати 60 секунд ----
        esp_sleep_enable_timer_wakeup(60ULL * 1000000ULL);
        esp_light_sleep_start();
    
        // ---- очистка статусу ----
        showStatus(" ");
      }


        // ---- OTA кожні 10 годин на 00 хвилин ----
        if ((tm.tm_min == 15) && (tm.tm_hour % 10 == 0))
        {
            checkForOTA();
        }
    
}



