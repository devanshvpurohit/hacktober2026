# SURDAS (VNR-main) — Comprehensive Project Issues & Audit Report

**Date:** October 2026  
**Audited Repository:** `VNR-main` (SURDAS Assistive Vision & Voice System for Visually Impaired)  
**Scope:** Embedded firmware (ESP32 / ESP32-CAM), Python AI/Vision/Voice Core, Navigation Subsystems, Caregiver Web Dashboard, Dependencies, Tests, and Documentation.

---

## Executive Summary

SURDAS is an ambitious assistive vision and navigation system combining dual ESP32 hardware, local computer vision (YOLOv8 + MiDaS depth), bilingual voice interaction, and offline spatial/pedestrian navigation. 

During this comprehensive audit, **24 distinct issues** were identified across safety-critical perception, firmware concurrency, voice command routing, hardware video streaming, dependency specifications, and test suites.

### Priority Severity Matrix

| Severity | Count | Primary Impact Areas |
|---|:---:|---|
| **CRITICAL** | 6 | Directional obstacle inversion (Safety), Command routing failure, ESP32 stream deadlock, Screen redraw loop lockup, Audio thread blocking, Permanent video disconnect |
| **HIGH** | 6 | Missing dependencies in `requirements.txt`, Dashboard video feed offline, Missing custom wake word model, Broken `--gui` CLI flag, Currency detector disconnected |
| **MEDIUM** | 7 | Test suite failure (`test_config.py`), Pytest plugin conflict, Name collisions (`PerceptionResult`, `NavigationState`), Unpooled SQLite connections, PyTorch/NumPy version pins |
| **LOW** | 5 | Offline violation in telemetry, Dead code in `surdas_brain.py`, Default model name inconsistency, Duplicated state initializations |

---

## 1. Critical Safety & Functional Issues

### 1.1 Spatial Direction Inversion (Left vs. Right Inversion)
- **File:** [`workers.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/workers.py#L139-L208)
- **Problem:** Inside `VisionWorker._loop()`, every video frame is horizontally mirrored:
  ```python
  frame = cv2.flip(frame, 1)
  ```
  Immediately afterward, spatial bounding boxes are calculated:
  ```python
  if cx < third_w:
      pos = "on your left"
  elif cx > 2 * third_w:
      pos = "on your right"
  ```
- **Safety Impact:** Mirroring the camera frame swaps the left and right sides of the image. An obstacle physically located on the user's **left** is projected to the right side of the flipped frame and verbally announced as **"on your right"**. For a visually impaired user navigating obstacles, this creates an acute collision hazard.
- **Remediation:** Remove `frame = cv2.flip(frame, 1)` or maintain raw camera orientation for spatial calculation and only flip during display if selfie-mode monitor view is explicitly desired.

---

### 1.2 Voice Command Router Caches `None` for Navigation & Spatial Memory
- **Files:** 
  - [`surdas_brain.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/surdas_brain.py#L201-L266)
  - [`voice/command_router.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/voice/command_router.py#L49-L97)
- **Problem:** In `SurdasBrain.__init__`, `self.voice_assistant` is initialized at line 201:
  ```python
  self.voice_assistant = VoiceAssistant(self, ...)
  ```
  Inside `VoiceAssistant.__init__`, `CommandRouter(brain, self.llm)` is created:
  ```python
  self.navigator = getattr(brain, "navigator", None)
  self.indoor_navigator = getattr(brain, "indoor_navigator", None)
  self.spatial_memory = getattr(brain, "spatial_memory", None)
  ```
  However, `self.navigator`, `self.spatial_memory`, and `self.indoor_navigator` are only created on `SurdasBrain` **later at lines 257–266**.
- **Impact:** `CommandRouter` permanently holds `None` for all three subsystems. When the user speaks:
  - *"Navigate to Charminar"*
  - *"Where is the chair?"*
  - *"Remember this room"*
  - *"Where am I?"*  
  All handlers immediately exit (`if not self.indoor_navigator: return False`) and fall through to Ollama general conversation instead of executing the navigation actions.
- **Remediation:** Convert `navigator`, `indoor_navigator`, and `spatial_memory` in `CommandRouter` into dynamic `@property` getters that read `getattr(self.brain, ...)` on demand.

---

### 1.3 ESP32-CAM Single-Threaded MJPEG Stream Deadlocks All Other Endpoints
- **File:** [`surdas_esp32_cam/surdas_esp32_cam.ino`](file:///Users/devanshvpurohit/Downloads/VNR-main/surdas_esp32_cam/surdas_esp32_cam.ino#L141-L158)
- **Problem:** `handleStream()` uses a blocking while loop on the main WebServer thread:
  ```cpp
  while (client.connected()) {
    camera_fb_t *fb = esp_camera_fb_get();
    ...
    delay(20);
  }
  ```
- **Impact:** Single-core Arduino `WebServer` cannot process any other HTTP request while `/stream` is active. While Python streams video:
  - `/led?state=on` or `/led?state=off` (torch control & OCR flash) **times out**.
  - `/status` **hangs and times out**.
  - `/capture` **fails**.
- **Remediation:** Implement a dual-task architecture using FreeRTOS `xTaskCreatePinnedToCore` for camera frame capture/streaming, or run camera streaming on a dedicated port/task.

---

### 1.4 ESP32 Controller TFT Redraw Loop Pegs CPU and Starves GPS UART
- **File:** [`surdas_esp32_controller/surdas_esp32_controller.ino`](file:///Users/devanshvpurohit/Downloads/VNR-main/surdas_esp32_controller/surdas_esp32_controller.ino#L540-L558)
- **Problem:** In `updateDisplay()`:
  ```cpp
  switch (fallState) {
    case FALL_CONFIRMED:  drawFallConfirmedFace(); return;
    case IMPACT_DETECTED: drawImpactFace();        return;
    case POSSIBLE_FALL:   drawPossibleFallFace();  return;
    ...
  ```
  Unlike `NORMAL` mode which checks `if (now - lastFaceDraw >= FACE_REFRESH_TIME)`, the fall states call `fillScreen()` and redraw the TFT **on every iteration of `loop()` without any cooldown**.
- **Impact:** Each 240x240 full-screen SPI render takes ~50ms. Calling it repeatedly:
  1. Blocks the CPU at 100% duty cycle.
  2. Causes the hardware serial buffer to overflow, dropping incoming NEO-6M GPS NMEA bytes.
  3. Starves `server.handleClient()`, causing the `/imu` and `/gps` HTTP endpoints to become unresponsive.
- **Remediation:** Add a refresh interval check or render state-change flag so fall screens are only drawn once upon state transition and updated at most once per second.

---

### 1.5 Missing Stream Reconnection in `CameraStream`
- **File:** [`surdas_brain.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/surdas_brain.py#L115-L125)
- **Problem:** In `CameraStream._read_loop()`:
  ```python
  ret, frame = self.cap.read()
  if ret and frame is not None:
      self.connected = True
      ...
  else:
      self.connected = False
      time.sleep(0.05)
  ```
  When the Wi-Fi connection to the ESP32-CAM drops or the ESP32 reboots, `cv2.VideoCapture.read()` returns `False` and never auto-reconnects to the network URL.
- **Impact:** A momentary 1-second Wi-Fi glitch permanently disables camera input until the Python script is manually killed and restarted.
- **Remediation:** When `self.connected` remains `False` for more than 2 seconds, release `self.cap` and attempt `self.cap = cv2.VideoCapture(self.src)`.

---

### 1.6 Whisper STT Invoked Synchronously in Audio Stream Thread
- **File:** [`voice/assistant.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/voice/assistant.py#L287-L290)
- **Problem:** During TTS barge-in checking in `_mic_loop()`:
  ```python
  buffer_audio = np.concatenate(self._tts_audio_buffer)
  text, _ = self.stt.transcribe(buffer_audio, sample_rate=self.sample_rate)
  ```
  `stt.transcribe()` runs the Whisper model on the CPU directly within the `_mic_loop` thread.
- **Impact:** Whisper execution blocks the audio loop for 400ms to 1.5 seconds. During this window, incoming microphone chunks accumulate in `self._audio_q` or get dropped, leading to audio stutter, buffer overflow, and delayed responses.
- **Remediation:** Delegate barge-in keyword verification to a lightweight background thread or rely exclusively on the low-latency `openWakeWord` neural detector for barge-in interrupts.

---

## 2. Broken Integrations & Orphaned Modules

### 2.1 Currency Detection Fully Implemented but Disconnected
- **Files:** 
  - [`currency_detector.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/currency_detector.py)
  - [`config.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/config.py#L123-L126)
  - [`surdas_brain.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/surdas_brain.py)
- **Problem:** `SmoothIndianCurrencyDetector` is complete with HSV color masks, contour bounding box analysis, and OCR denomination verification for all Indian banknotes (₹10 to ₹500). `config.py` also defines `CURRENCY_HISTORY_SIZE` and `CURRENCY_MIN_VOTES`. However, it is never imported or initialized in `surdas_brain.py`, and no voice command or keybinding triggers it.
- **Remediation:** Wire `SmoothIndianCurrencyDetector` into `CommandRouter` (e.g., phrases like *"How much money is this?"*, *"Check currency"*) and provide a key binding (e.g., `'c'`).

---

### 2.2 SafetyEngine Documented but Not Utilized by Workers
- **Files:** 
  - [`safety_engine.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/safety_engine.py)
  - [`workers.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/workers.py#L6)
- **Problem:** `workers.py` states in its header that `SafetyWorker` *"Reads PerceptionResult → runs SafetyEngine → triggers CRITICAL_SAFETY TTS"*. However, `SafetyEngine` is never imported or called in `workers.py`. Instead, `workers.py` uses simplified ad-hoc threshold checks, ignoring the multi-frame tracking, closing velocity estimation, and obstacle categorization logic in `safety_engine.py`.
- **Remediation:** Integrate `SafetyEngine` into `SafetyWorker` to enable multi-frame tracking and prevent single-frame false alerts.

---

### 2.3 Caregiver Dashboard Video Stream Disconnected by Default
- **Files:** 
  - [`caregiver_dashboard/src/App.tsx`](file:///Users/devanshvpurohit/Downloads/VNR-main/caregiver_dashboard/src/App.tsx#L72)
  - [`launch_dashboard.sh`](file:///Users/devanshvpurohit/Downloads/VNR-main/launch_dashboard.sh#L126)
  - [`app.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/app.py#L32-L59)
- **Problem:** `App.tsx` expects the video feed at:
  ```typescript
  const VIDEO_FEED = 'http://localhost:8888/video_feed';
  ```
  This endpoint is hosted only by `app.py`. However, `launch_dashboard.sh` starts `surdas_brain.py` (which hosts FastAPI telemetry on port 8000, without a `/video_feed` endpoint).
- **Impact:** The video stream panel on the Caregiver Dashboard displays a broken image icon.
- **Remediation:** Either mount the `/video_feed` streaming endpoint directly into `telemetry.py` (FastAPI), or update `launch_dashboard.sh` to coordinate `app.py`.

---

### 2.4 Missing Custom Wake Word Model File (`models/surdas.onnx`)
- **Files:**
  - [`voice/wakeword.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/voice/wakeword.py#L14)
  - Directory: `models/`
- **Problem:** `voice/wakeword.py` references `models/surdas.onnx`. In the filesystem, only `models/surdas.onnx.data` (external tensor data) exists. The protobuf graph file `surdas.onnx` is missing.
- **Impact:** `os.path.exists(_SURDAS_ONNX)` returns `False`. The custom "Surdas" neural wake-word detector fails to load, falling back to stock generic openWakeWord models or text matching.
- **Remediation:** Commit or restore the missing `models/surdas.onnx` graph definition file.

---

### 2.5 Broken `--gui` CLI Option & Conflicting GUI Files
- **Files:** 
  - [`surdas_brain.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/surdas_brain.py#L40-L48, #L1141-L1144)
  - [`launch_gui.sh`](file:///Users/devanshvpurohit/Downloads/VNR-main/launch_gui.sh)
  - [`surdas_gui.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/surdas_gui.py)
  - [`surdas_gui_tk.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/surdas_gui_tk.py)
- **Problem:**
  1. `surdas_brain.py` accepts `--gui`, but `if __name__ == "__main__":` unconditionally runs `brain.run()`, completely ignoring the flag.
  2. `launch_gui.sh` states it launches the Tkinter desktop app, but executes `python3 surdas_brain.py --gui`.
  3. `surdas_gui.py` uses `PyQt5`, which is not in `requirements.txt` and fails on Python 3.13 macOS ARM. Meanwhile, `surdas_gui_tk.py` uses built-in Tkinter.
- **Remediation:** Update `surdas_brain.py` to launch `surdas_gui_tk.py` when `--gui` is passed.

---

## 3. Dependency & Environment Deficiencies

### 3.1 Unlisted Mandatory Dependencies in `requirements.txt`
- **File:** [`requirements.txt`](file:///Users/devanshvpurohit/Downloads/VNR-main/requirements.txt)
- **Problem:** Multiple packages imported in the main execution paths are absent:
  - `fastapi` & `uvicorn`: Unconditionally imported in `telemetry.py` (started on boot by `surdas_brain.py`).
  - `flask`: Imported in `app.py`.
  - `pyserial`: Commented out (`# pyserial>=3.5`), but required by `navigation/location.py` whenever GPS is enabled.
  - `requests`: Required by `test_imu_endpoint.py` and Valhalla setup.
- **Impact:** Clean installations via `pip install -r requirements.txt` immediately crash on `import uvicorn` or `import fastapi`.
- **Remediation:** Add `fastapi>=0.100.0`, `uvicorn>=0.22.0`, `requests>=2.28.0`, and uncomment `pyserial`.

---

### 3.2 Overly Restrictive Version Pins on Modern Python (3.13)
- **File:** [`requirements.txt`](file:///Users/devanshvpurohit/Downloads/VNR-main/requirements.txt#L2-L22)
- **Problem:**
  - `numpy>=1.24.0,<2.0.0`: Python 3.13 requires NumPy 2.x wheels; NumPy 1.x fails to compile without legacy toolchains.
  - `torch>=2.0.0,<2.5.0`: Python 3.13 requires PyTorch 2.5+ for native wheels.
- **Remediation:** Relax pins to `numpy>=1.24.0` and `torch>=2.0.0`.

---

### 3.3 Dashboard Missing `node_modules`
- **File:** `caregiver_dashboard/`
- **Problem:** `caregiver_dashboard/` does not have dependencies pre-installed. `npm run build` fails with `tsc: command not found`. While `launch_dashboard.sh` contains an `npm install` fallback, standalone builds fail.
- **Remediation:** Document running `cd caregiver_dashboard && npm install` or add an automated check in setup scripts.

---

## 4. Test Suite Inconsistencies & Code Duplications

### 4.1 Unit Test Assertion Failure: `test_classify_depth_proximity`
- **File:** [`tests/test_config.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/tests/test_config.py#L47)
- **Problem:** Running the test suite yields:
  ```text
  FAILED tests/test_config.py::test_classify_depth_proximity - AssertionError: assert 'VERY_CLOSE' == 'CLOSE'
  ```
  `test_config.py` asserts `classify_depth_proximity(800) == "CLOSE"`. However, in `config.py`:
  ```python
  DEPTH_VERY_CLOSE_THRESHOLD = float(os.getenv("SURDAS_DEPTH_VERY_CLOSE", "480"))
  ```
  Since `800 >= 480`, it correctly evaluates to `"VERY_CLOSE"`. The test was not updated when threshold defaults were adjusted.
- **Remediation:** Update test cases to match the active threshold values (e.g. test with 450 for CLOSE).

---

### 4.2 Pytest Crash via `langsmith` Plugin Incompatibility
- **Problem:** Running `pytest tests/` fails with:
  ```text
  ImportError: cannot import name 'appengine' from 'urllib3.contrib'
  ```
  The global `langsmith` pytest plugin imports `requests_toolbelt._compat`, which breaks under modern `urllib3 v2.x`.
- **Remediation:** Add `pytest.ini` in project root with:
  ```ini
  [pytest]
  addopts = -p no:langsmith
  ```

---

### 4.3 Duplicate Class & Enum Definitions
- **Class Name Collision (`PerceptionResult`):**
  - Defined in [`workers.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/workers.py#L40) (stores frame, depth_colormap, yolo_detections, etc.).
  - Defined in [`indoor_perception.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/indoor_perception.py#L508) (stores occupancy_grid, safe_directions, etc.).
- **Enum Collision (`NavigationState`):**
  - Defined in [`system_state.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/system_state.py#L49).
  - Defined in [`indoor_navigator.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/indoor_navigator.py#L57).
- **Impact:** Increases cognitive load and prevents unified type annotations.
- **Remediation:** Rename `indoor_perception.PerceptionResult` to `IndoorPerceptionResult` and import `NavigationState` from `system_state.py`.

---

## 5. Architectural & Code Quality Cleanups

### 5.1 Telemetry `/location` Violates Offline Policy
- **File:** [`telemetry.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/telemetry.py#L41-L62)
- **Problem:** The `/location` endpoint calls `http://ipinfo.io/json` with a 5.0s timeout. This fails when offline, incurs 5-second HTTP hangs, and leaks user network data rather than returning GPS telemetry.
- **Remediation:** Return coordinates from the local GPS provider or navigator instead of querying external IP geolocation.

---

### 5.2 Dead Code in `surdas_brain.py` (`process_navigation`)
- **File:** [`surdas_brain.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/surdas_brain.py#L500-L780)
- **Problem:** `process_navigation()` spans ~280 lines containing legacy monolithic YOLO + MiDaS logic. Since `VisionWorker` and `SafetyWorker` handle inference in background threads, `process_navigation()` is never called in `surdas_brain.py`.
- **Remediation:** Remove legacy `process_navigation()` or refactor into dedicated test utilities.

---

### 5.3 Inconsistent LLM Model Defaults Across Configs
- **Files:**
  - [`config.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/config.py#L115): `LLM_DEFAULT_MODEL = "gemma2:2b"`
  - [`voice/llm.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/voice/llm.py#L24): `DEFAULT_MODEL = "gemma3:1b"`
  - [`surdas_brain.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/surdas_brain.py#L24): CLI help states `gemma3:1b`.
- **Remediation:** Align `config.py` to point to `gemma3:1b` or reference `config.LLM_DEFAULT_MODEL` uniformly.

---

### 5.4 Unpooled SQLite Database Access in `SpatialMemory`
- **File:** [`spatial_memory.py`](file:///Users/devanshvpurohit/Downloads/VNR-main/spatial_memory.py)
- **Problem:** Every single query (`add_room`, `get_room_by_name`, `add_object`, `find_objects`, etc.) executes `conn = sqlite3.connect(self.db_path)` and `conn.close()`.
- **Impact:** High disk I/O latency when processing detections at video frame rates (15–30 FPS).
- **Remediation:** Maintain a single persistent connection with thread locking or use a connection context manager.

---

## 6. Actionable Fix Checklist

- [x] **Fix Left/Right inversion:** In `workers.py`, conditioned `cv2.flip(frame, 1)` on `SURDAS_MIRROR_CAMERA` so real-world left matches image left by default.
- [x] **Fix command router:** Updated `CommandRouter` in `voice/command_router.py` to use dynamic properties for `navigator`, `indoor_navigator`, and `spatial_memory`.
- [x] **Fix CameraStream reconnection:** Added automatic retry/re-open loop in `CameraStream._read_loop()` in `surdas_brain.py`.
- [x] **Connect Currency Detector:** Added `CURRENCY_CHECK` intent to `i18n_phrases.py`, `CommandRouter`, and added `process_currency` + `'c'` key in `surdas_brain.py`.
- [x] **Update `requirements.txt`:** Added `fastapi`, `uvicorn`, `flask`, `requests`, `tqdm`, uncommented `pyserial`, and relaxed version pins for Python 3.13.
- [x] **Fix test assertion:** Adjusted `test_classify_depth_proximity` in `tests/test_config.py` to match current depth thresholds (all 24 tests pass).
- [x] **Fix `--gui` flag:** Connected `--gui` in `surdas_brain.py` to start `surdas_gui_tk.py`.
- [x] **Fix telemetry location:** Made `/location` offline-safe with local GPS endpoint prioritization and Hyderabad offline fallback.
- [x] **Fix pytest conflict:** Added `pytest.ini` and `run_tests.sh` to prevent `langsmith` entrypoint conflict.
