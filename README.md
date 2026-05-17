# 🔴 MYTHOS NEMESIS v2.0

**Anti-Online-Gambling Intelligence & Takedown Platform**

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Kali%20Linux-blue" />
  <img src="https://img.shields.io/badge/Python-3.13-green" />
  <img src="https://img.shields.io/badge/License-MIT-red" />
  <img src="https://img.shields.io/badge/Status-Beta-orange" />
</p>

---

## 🛡️ Overview

MYTHOS NEMESIS is a comprehensive intelligence platform designed to combat online gambling operations. Built with a SpiderFoot-like web GUI, it provides real-time scanning, intelligence gathering, and takedown capabilities for law enforcement and cybersecurity professionals.

**Credit**: ibnu qory nur fikri / Dorakula

## ⚡ Features

### Core Modules
- **Dashboard** — Real-time scan monitoring with log-rain visualization
- **New Scan** — Multi-target scanning with 45+ Kali Linux tools integration
- **6-Layer Intelligence** — Domain → Content → Infra → Financial → Network → Historical
- **Legal Kill Chain** — DETECT → TRACE → STRANGLE → BLOCK → MONITOR
- **Blocklist Manager** — Automated blocking with evidence-based entries
- **Tools Panel** — Direct access to 45+ security tools
- **Terminal** — Real-time scan log streaming via SocketIO
- **IP Tracker** — Geo-IP lookup, reverse DNS, ASN/ISP detection, WHOIS, traceroute, nmap, abuse contacts

### Intelligence Capabilities
- Domain & subdomain enumeration
- Web vulnerability scanning
- Payment gateway detection
- Hosting provider identification
- VPN/proxy detection
- WHOIS & DNS analysis
- Network infrastructure mapping
- Historical data correlation

### Legal Kill Chain
1. **DETECT** — Identify gambling domains and infrastructure
2. **TRACE** — Trace ownership, hosting, and financial flows
3. **STRANGLE** — Cut off resources (hosting, DNS, payment)
4. **BLOCK** — Block access at ISP/national level
5. **MONITOR** — Continuous surveillance for re-emergence

## 🏗️ Architecture

```
MYTHOS NEMESIS v2.0
├── mythos.py          # Flask + SocketIO backend (2700+ lines)
├── templates/
│   └── index.html     # Dashboard HTML
├── static/
│   ├── css/
│   │   └── style.css  # Hacker theme (pure black, glassmorphism)
│   └── js/
│       └── app.js     # SocketIO client, UI logic
├── data/              # SQLite databases
├── evidence/          # Collected evidence
├── logs/              # Scan logs
└── reports/           # Generated reports
```

## 🚀 Installation

### Prerequisites
- Kali Linux 2026.1+
- Python 3.13+
- 45+ security tools (auto-detected)

### Quick Start
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/mythos-nemesis.git
cd mythos-nemesis

# Install dependencies
pip install flask flask-socketio

# Run the platform
python mythos.py

# Access dashboard
# Open browser: http://localhost:5000
```

## 🎨 Theme

- **Background**: Pure black (#000000)
- **Text**: White (#FFFFFF)
- **Panels**: Glassmorphism with backdrop blur
- **Animation**: Log-rain canvas + CRT scanline overlay
- **Font**: JetBrains Mono monospace

## ⚠️ Legal Disclaimer

This tool is designed **strictly for legal use** by authorized law enforcement and cybersecurity professionals. It follows a **legal kill chain** approach:

- ❌ **NO DDoS** attacks
- ❌ **NO unauthorized access**
- ✅ Intelligence gathering only
- ✅ Evidence-based reporting
- ✅ Coordination with authorities (Kominfo, Polri, BSSN, OJK)

## 📋 Requirements

- Flask
- Flask-SocketIO
- Python 3.13+
- Kali Linux tools (nmap, whois, dig, traceroute, etc.)

## 📜 License

MIT License — Free for legal cybersecurity and law enforcement use.

---

**Built with 🔴 by ibnu qory nur fikri / Dorakula**
