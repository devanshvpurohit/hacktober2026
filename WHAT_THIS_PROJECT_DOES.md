# What This Project Does — SURDAS (VNR-main)

**Assistive vision and navigation system for visually impaired users.**

Combines dual ESP32 hardware with local computer vision (YOLOv8 + MiDaS depth), bilingual voice interaction, and offline spatial/pedestrian navigation. Includes firmware (ESP32/ESP32-CAM), Python AI core, caregiver web dashboard, and test suites.

**Key capabilities:**
- Real-time obstacle detection and verbal description (with known left/right inversion bug)
- Voice command routing for navigation, spatial memory, and fall detection
- GPS/telemetry and caregiver dashboard
- Custom wake word detection (missing model file)
- Indian currency recognition (disconnected module)
- Offline spatial memory via SQLite