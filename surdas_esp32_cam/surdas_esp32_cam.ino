// =====================================================
//
//                    SURDAS
//              ESP32-CAM Optical Transmitter
//
//   192.168.4.1  (AP host — SSID: SURDAS_EYES)
//
//   Hardware: AI-Thinker ESP32-CAM (OV2640)
//   Flash LED: GPIO4
//
//   Endpoints:
//     /stream   — MJPEG live stream (for YOLO / Python)
//     /capture  — Single JPEG snapshot
//     /led      — Flash control (?state=on|off|auto)
//     /status   — JSON status (includes DevKit GPS proxy)
//     /         — Simple info page with stream embed
//
//   DevKit sits at 192.168.4.2  (/gps  /imu  /status)
//
// =====================================================

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>   // to proxy DevKit /status for CORS-free access


// =====================================================
// WIFI — run as AP so DevKit can connect
// =====================================================

const char* AP_SSID     = "SURDAS_EYES";
const char* AP_PASSWORD = "12345678";

// DevKit lives at this IP on our AP subnet
const char* DEVKIT_IP = "192.168.4.2";

WebServer server(80);


// =====================================================
// AI-THINKER ESP32-CAM PIN DEFINITIONS
// =====================================================

#define PWDN_GPIO_NUM   32
#define RESET_GPIO_NUM  -1
#define XCLK_GPIO_NUM    0
#define SIOD_GPIO_NUM   26
#define SIOC_GPIO_NUM   27
#define Y9_GPIO_NUM     35
#define Y8_GPIO_NUM     34
#define Y7_GPIO_NUM     39
#define Y6_GPIO_NUM     36
#define Y5_GPIO_NUM     21
#define Y4_GPIO_NUM     19
#define Y3_GPIO_NUM     18
#define Y2_GPIO_NUM      5
#define VSYNC_GPIO_NUM  25
#define HREF_GPIO_NUM   23
#define PCLK_GPIO_NUM   22

#define FLASH_LED_PIN    4   // Onboard high-power flash LED

bool flashAutoMode = false;  // auto-flash when dark (future)


// =====================================================
// CAMERA INITIALIZATION
// =====================================================

bool initCamera() {
  camera_config_t config;
  config.ledc_channel   = LEDC_CHANNEL_0;
  config.ledc_timer     = LEDC_TIMER_0;
  config.pin_d0         = Y2_GPIO_NUM;
  config.pin_d1         = Y3_GPIO_NUM;
  config.pin_d2         = Y4_GPIO_NUM;
  config.pin_d3         = Y5_GPIO_NUM;
  config.pin_d4         = Y6_GPIO_NUM;
  config.pin_d5         = Y7_GPIO_NUM;
  config.pin_d6         = Y8_GPIO_NUM;
  config.pin_d7         = Y9_GPIO_NUM;
  config.pin_xclk       = XCLK_GPIO_NUM;
  config.pin_pclk       = PCLK_GPIO_NUM;
  config.pin_vsync      = VSYNC_GPIO_NUM;
  config.pin_href       = HREF_GPIO_NUM;
  config.pin_sscb_sda   = SIOD_GPIO_NUM;
  config.pin_sscb_scl   = SIOC_GPIO_NUM;
  config.pin_pwdn       = PWDN_GPIO_NUM;
  config.pin_reset      = RESET_GPIO_NUM;
  config.xclk_freq_hz   = 20000000;
  config.pixel_format   = PIXFORMAT_JPEG;

  if (psramFound()) {
    config.frame_size  = FRAMESIZE_QVGA;  // 320×240 — fast enough for YOLO
    config.jpeg_quality = 10;             // 10–63: lower = better quality
    config.fb_count    = 2;
    config.grab_mode   = CAMERA_GRAB_LATEST;
    config.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    config.frame_size  = FRAMESIZE_QQVGA;
    config.jpeg_quality = 15;
    config.fb_count    = 1;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[CAM] Init failed: 0x%x\n", err);
    return false;
  }

  // Image tuning for computer vision
  sensor_t *s = esp_camera_sensor_get();
  s->set_brightness(s,  1);  // slight brightness boost
  s->set_contrast(s,    1);
  s->set_saturation(s,  0);
  s->set_whitebal(s,    1);  // auto white balance
  s->set_gain_ctrl(s,   1);  // auto gain
  s->set_exposure_ctrl(s, 1); // auto exposure
  s->set_hmirror(s,     0);
  s->set_vflip(s,       0);

  Serial.println("[CAM] OV2640 ready");
  return true;
}


// =====================================================
// ENDPOINT: /stream — MJPEG live stream
// =====================================================

void handleStream() {
  WiFiClient client = server.client();
  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: multipart/x-mixed-replace; boundary=frame");
  client.println("Access-Control-Allow-Origin: *");
  client.println("Cache-Control: no-cache");
  client.println();

  while (client.connected()) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("[CAM] Frame capture failed");
      break;
    }
    client.printf(
      "--frame\r\n"
      "Content-Type: image/jpeg\r\n"
      "Content-Length: %u\r\n\r\n",
      fb->len
    );
    client.write(fb->buf, fb->len);
    client.print("\r\n");
    esp_camera_fb_return(fb);
    delay(20);  // ~50 fps max; WiFi will throttle naturally
  }
}


// =====================================================
// ENDPOINT: /capture — single high-quality JPEG
// =====================================================

void handleCapture() {
  // Temporarily switch to higher resolution for snapshot
  sensor_t *s = esp_camera_sensor_get();
  s->set_framesize(s, FRAMESIZE_VGA);  // 640×480 for OCR / text
  delay(150);

  camera_fb_t *fb = esp_camera_fb_get();

  // Restore streaming resolution
  s->set_framesize(s, psramFound() ? FRAMESIZE_QVGA : FRAMESIZE_QQVGA);

  if (!fb) {
    server.send(500, "text/plain", "Capture failed");
    return;
  }

  server.sendHeader("Content-Type",   "image/jpeg");
  server.sendHeader("Content-Length", String(fb->len));
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send_P(200, "image/jpeg", (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
}


// =====================================================
// ENDPOINT: /led — flash LED control
//   ?state=on   — turn on
//   ?state=off  — turn off
//   ?state=auto — auto mode (not yet implemented)
// =====================================================

void handleLed() {
  if (!server.hasArg("state")) {
    server.send(400, "text/plain", "Missing ?state=on|off|auto");
    return;
  }
  String state = server.arg("state");
  if (state == "on") {
    flashAutoMode = false;
    digitalWrite(FLASH_LED_PIN, HIGH);
    server.send(200, "text/plain", "LED ON");
  } else if (state == "off") {
    flashAutoMode = false;
    digitalWrite(FLASH_LED_PIN, LOW);
    server.send(200, "text/plain", "LED OFF");
  } else if (state == "auto") {
    flashAutoMode = true;
    server.send(200, "text/plain", "LED AUTO");
  } else {
    server.send(400, "text/plain", "Invalid state");
  }
}


// =====================================================
// ENDPOINT: /status — CAM status + DevKit GPS proxy
// =====================================================

void handleStatus() {
  // Try to pull the DevKit's GPS JSON (non-blocking with 500 ms timeout)
  String devkitJson = "null";
  HTTPClient http;
  http.begin("http://" + String(DEVKIT_IP) + "/status");
  http.setTimeout(500);
  int code = http.GET();
  if (code == 200) {
    devkitJson = http.getString();
  }
  http.end();

  bool hasPSRAM = psramFound();
  String j = "{";
  j += "\"device\":\"SURDAS_CAM\"";
  j += ",\"model\":\"AI-Thinker\"";
  j += ",\"ip\":\""   + WiFi.softAPIP().toString() + "\"";
  j += ",\"ssid\":\"" + String(AP_SSID) + "\"";
  j += ",\"clients\":" + String(WiFi.softAPgetStationNum());
  j += ",\"psram\":"   + String(hasPSRAM ? "true" : "false");
  j += ",\"flash\":"   + String(digitalRead(FLASH_LED_PIN) ? "true" : "false");
  j += ",\"devkit\":"  + devkitJson;
  j += "}";

  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", j);
}


// =====================================================
// ENDPOINT: / — simple info + stream page
// =====================================================

void handleRoot() {
  String ip = WiFi.softAPIP().toString();
  String html = "<!DOCTYPE html><html><head>"
    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>SURDAS CAM</title>"
    "<style>body{background:#05070a;color:#fff;font-family:Arial,sans-serif;text-align:center;padding:20px}"
    "h1{color:#00ffff}img{max-width:100%;border-radius:12px;margin:12px 0}"
    "a{color:#00ffff}p{color:#8ca0b3;margin:6px 0}</style></head><body>"
    "<h1>SURDAS CAM</h1>"
    "<p>AI-Thinker ESP32-CAM &mdash; AP Host</p>"
    "<img src='/stream' alt='Live Stream'><br>"
    "<p><a href='/capture'>&#128247; Capture snapshot</a></p>"
    "<p><a href='/led?state=on'>&#128161; Flash ON</a> &nbsp; "
    "<a href='/led?state=off'>&#128161; Flash OFF</a></p>"
    "<p><a href='/status'>&#9881; Status JSON</a></p>"
    "<hr style='border-color:#203040;margin:16px 0'>"
    "<p style='color:#00ffff'>DevKit dashboard: <a href='http://192.168.4.2/'>http://192.168.4.2/</a></p>"
    "</body></html>";
  server.send(200, "text/html", html);
}


// =====================================================
// SETUP & LOOP
// =====================================================

void setup() {
  Serial.begin(115200);
  delay(500);

  Serial.println("\n================================");
  Serial.println("    SURDAS OPTICAL TRANSMITTER");
  Serial.println("================================");

  pinMode(FLASH_LED_PIN, OUTPUT);
  digitalWrite(FLASH_LED_PIN, LOW);

  // Brief flash to indicate boot
  digitalWrite(FLASH_LED_PIN, HIGH);
  delay(80);
  digitalWrite(FLASH_LED_PIN, LOW);

  if (!initCamera()) {
    Serial.println("[SURDAS] FATAL: Camera init failed. Halting.");
    while (true) delay(1000);
  }

  // Start AP
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASSWORD);

  Serial.print("[WIFI] AP started. IP: ");
  Serial.println(WiFi.softAPIP());
  Serial.print("[WIFI] SSID: ");
  Serial.println(AP_SSID);

  // Routes
  server.on("/stream",  HTTP_GET, handleStream);
  server.on("/capture", HTTP_GET, handleCapture);
  server.on("/led",     HTTP_GET, handleLed);
  server.on("/status",  HTTP_GET, handleStatus);
  server.on("/",        HTTP_GET, handleRoot);
  server.begin();

  Serial.println("[HTTP] Server started");
  Serial.println();
  Serial.println("Endpoints:");
  Serial.print("  Stream:  http://"); Serial.print(WiFi.softAPIP()); Serial.println("/stream");
  Serial.print("  Capture: http://"); Serial.print(WiFi.softAPIP()); Serial.println("/capture");
  Serial.print("  Status:  http://"); Serial.print(WiFi.softAPIP()); Serial.println("/status");
  Serial.println("================================");
}

void loop() {
  server.handleClient();
  delay(1);
}
