# 💡 LightLink — File Transfer Over Visible Light

> Send files between an offline computer and a phone using nothing but a screen and a camera — no WiFi, no Bluetooth, no cellular network required.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Desktop%20%2B%20Mobile%20Browser-lightgrey)](#)


---

## 📖 Overview

LightLink is an experimental **optical data transfer system**: a sender application encodes a file into a rapid sequence of QR codes and displays them full-screen; a receiver — running entirely in a mobile browser — decodes the stream via the device camera and reconstructs the original file. No network connection is required at any point in the transfer itself.

This project was built to explore a practical question: **can two devices exchange files when every conventional network channel (WiFi, Bluetooth, cellular) is unavailable?** The answer turned out to involve a genuinely interesting constraint — browser camera permissions require a "secure context" (`https://` or `localhost`), which shapes the entire architecture of the offline deployment.

## ✨ Features

- 📤 **Sender (Python + OpenCV)** — splits any file into chunks, encodes each as a QR code with CRC32 integrity checking, and loops the sequence full-screen until the transfer completes
- 📥 **Receiver (vanilla JS, zero dependencies at runtime)** — scans the screen via `getUserMedia`, verifies each chunk's checksum, reassembles the file in-browser, and offers it as a direct download
- 🌐 **Three deployment modes** for different levels of network availability — from "fully online" down to "airplane mode, no network stack functioning at all"
- 🔁 **Self-healing transfer** — no acknowledgment channel needed; the sender loops continuously so any frame the camera misses simply gets rebroadcast on the next pass

## 🏗️ Architecture

```mermaid
flowchart LR
    A[File] -->|chunked + CRC32| B[QR Code Sequence]
    B -->|full-screen loop| C[Computer Display]
    C -->|camera capture| D[Phone Browser]
    D -->|jsQR decode + verify| E[Reassembled Chunks]
    E -->|Blob + download| F[Original File]
```

**Transfer protocol** (plain-text, human-inspectable):

```
META|<total_chunks>|<total_size>|<base64_filename>
F<index>/<total>|<crc32_hex>|<base64_payload>
```

## 🧩 The Interesting Part: Solving for "Truly Offline"

Getting the *concept* working (screen → camera QR relay) is the easy 20%. The hard 80% was making it usable when there is genuinely **no network of any kind** — because browsers refuse camera access outside a secure context, ruling out plain `file://` and plain `http://` on a local network out of the box.

This repo documents three progressively more offline-tolerant solutions:

| Mode | Network requirement | How camera permission is satisfied |
|---|---|---|
| **Online** | Internet, both ends | Standard HTTPS page |
| **LAN-only** | Local WiFi/hotspot, no internet | Self-signed cert + local HTTPS server (`serve_offline.py`) |
| **Fully offline** | Literally none | Receiver pre-installed on-device; served via `localhost` (secure by spec regardless of connectivity) using Termux on Android |

## 🚀 Getting Started

### Prerequisites

```bash
pip install qrcode opencv-python pillow numpy
```

### 1. Sender (run on the computer with the file)

```bash
python sender/sender.py path/to/your/file.jpg
```

Optional flags:

| Flag | Default | Purpose |
|---|---|---|
| `--chunk` | `300` | Bytes of raw data per QR frame — lower it if the camera struggles to scan |
| `--delay` | `0.25` | Seconds each frame is displayed |
| `--size` | `800` | QR code render size in pixels |

### 2. Receiver (run on the phone)

Pick the deployment mode that matches your network situation — see [`docs/deployment-modes.md`](docs/deployment-modes.md) for full instructions on each of the three modes above.

Quickest path (same WiFi, no internet needed):

```bash
python receiver/serve_offline.py
# → open the printed https://<ip>:8443/receiver_offline.html on the phone
```

## 📊 Performance

Throughput is roughly **1–5 KB/s**, bottlenecked by camera focus speed and screen refresh timing rather than QR decode speed itself. This is adequate for small files (config files, keys, short documents) but not intended as a general-purpose transfer method — it's a fallback for when nothing else works.

## 🛠️ Tech Stack

- **Sender:** Python, OpenCV, `qrcode`, NumPy
- **Receiver:** Vanilla JavaScript, [jsQR](https://github.com/cozmo/jsQR), HTML5 `getUserMedia` / Canvas API
- **Offline serving:** Python `http.server` + `ssl`, self-signed X.509 certs via `cryptography`

## 📁 Project Structure

```
light-file-transfer/
├── sender/
│   └── sender.py
├── receiver/
│   ├── receiver.html
│   ├── receiver_offline.html
│   └── serve_offline.py
├── docs/
│   └── screenshots/
├── README.md
└── LICENSE
```

## 🗺️ Roadmap

- [ ] Replace loop-based rebroadcast with fountain coding (RaptorQ) for more efficient bandwidth use
- [ ] Auto-downscale/compress images before transfer
- [ ] iOS-compatible fully-offline flow (currently Android/Termux only)

## 📄 License

MIT — see [LICENSE](LICENSE).

---

*Built as an exploration of browser security constraints (secure contexts) and offline-first system design.*
