# Project Issues Summary — SURDAS (VNR-main)

**Ponytail mode:** full

**Total issues:** 24 across 6 categories (from comprehensive audit)

| Severity | Count | Key Areas |
|---|---:|---|
| **CRITICAL** | 6 | Directional inversion, command routing deadlock, ESP32 stream deadlock, TFT redlock, video disconnect, audio thread blocking |
| **HIGH** | 6 | Missing dependencies, dashboard video offline, wake word model missing, broken `--gui` flag, currency detector disconnected |
| **MEDIUM** | 7 | Test failures, pytest plugin conflicts, name collisions, unpooled SQLite, version pins |
| **LOW** | 5 | Offline telemetry violation, dead code, model name inconsistency, duplicated init |

---
**Critical (must-fix):** Spatial left/right inversion (safety), ESP32 stream deadlock, command router None caching
**High:** Missing deps in requirements.txt, broken GUI flag, missing wake word model
**Medium:** Test assertion mismatches, pytest langsmith conflict, class/enum collisions
**Low:** Dead code, model name inconsistency, offline telemetry

---
**Reference:** Full detailed audit in `PROJECT_ISSUES_AUDIT.md` (315 lines, all 24 issues with file locations and remediations).