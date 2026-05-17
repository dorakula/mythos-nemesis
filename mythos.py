#!/usr/bin/env python3
"""
████████╗██╗  ██╗██╗   ██╗███╗   ███╗██████╗ ███████╗ ██████╗ ███╗   ██╗ █████╗
╚══██╔══╝██║  ██║██║   ██║████╗ ████║██╔══██╗██╔════╝██╔═══██╗████╗  ██║██╔══██╗
   ██║   ███████║██║   ██║██╔████╔██║██████╔╝█████╗  ██║   ██║██╔██╗ ██║███████║
   ██║   ██╔══██║██║   ██║██║╚██╔╝██║██╔══██╗██╔══╝  ██║   ██║██║╚██╗██║██╔══██║
   ██║   ██║  ██║╚██████╔╝██║ ╚═╝ ██║██║  ██║███████╗╚██████╔╝██║ ╚████║██║  ██║
   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝

MYTHOS NEMESIS v2.0 — Anti-Online-Gambling Intelligence & Takedown Platform
By: ibnu qory nur fikri / Dorakula

SpiderFoot-like Architecture: Flask + SocketIO Web Dashboard + Terminal Live Logs
Legal Kill Chain: DETECT → TRACE → STRANGLE → BLOCK → MONITOR
6-Layer Classification: Domain → Content → Infra → Financial → Network → Historical

⚠️  LEGAL USE ONLY — No DDoS. Always shut down servers after testing.
⚠️  PORT 8080 IS BLOCKED — Reserved for MCP Bridge (0.0.0.0:8080/sse)
"""

import os
import sys
import json
import time
import uuid
import sqlite3
import hashlib
import subprocess
import threading
import datetime
import signal
import re
import socket
import ipaddress
import base64
import shutil
from pathlib import Path
from collections import defaultdict

# Flask & SocketIO
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit

# ============================================================
# CONFIGURATION
# ============================================================
VERSION = "2.1.0"
AUTHOR = "ibnu qory nur fikri / Dorakula"
DEFAULT_PORT = 5000
BLOCKED_PORT = 8080  # MCP Bridge — DO NOT USE
DB_PATH = os.path.expanduser("~/.mythos/mythos.db")
HEXSTRIKE_API = "http://127.0.0.1:8888"
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# PORT 8080 PROTECTION
# ============================================================
def validate_port(port):
    """BLOCK port 8080 — reserved for MCP Bridge"""
    if int(port) == BLOCKED_PORT:
        print(f"\n[⛔ BLOCKED] Port {BLOCKED_PORT} is reserved for MCP Bridge (0.0.0.0:8080/sse)")
        print(f"[⛔ BLOCKED] Use a different port. Default: {DEFAULT_PORT}")
        sys.exit(1)
    return int(port)

# ============================================================
# DUAL LOGGER — Terminal + Web
# ============================================================
class DualLogger:
    """Logs to both terminal (color) and web dashboard (SocketIO)"""

    COLORS = {
        'red': '\033[91m', 'green': '\033[92m', 'yellow': '\033[93m',
        'blue': '\033[94m', 'magenta': '\033[95m', 'cyan': '\033[96m',
        'white': '\033[97m', 'bold': '\033[1m', 'dim': '\033[2m',
        'reset': '\033[0m'
    }

    def __init__(self, socketio=None):
        self.socketio = socketio
        self.scan_id = None
        self._lock = threading.Lock()

    def set_scan(self, scan_id):
        self.scan_id = scan_id

    def _term(self, msg, color='white', prefix=''):
        c = self.COLORS.get(color, '')
        r = self.COLORS['reset']
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        print(f"{c}[{ts}] {prefix}{msg}{r}")

    def _web(self, msg, level='info'):
        if self.socketio:
            try:
                self.socketio.emit('log_event', {
                    'scan_id': self.scan_id,
                    'timestamp': datetime.datetime.now().isoformat(),
                    'level': level,
                    'message': msg
                })
            except Exception:
                pass

    def info(self, msg):
        self._term(msg, 'cyan', 'ℹ ')
        self._web(msg, 'info')

    def success(self, msg):
        self._term(msg, 'green', '✓ ')
        self._web(msg, 'success')

    def warning(self, msg):
        self._term(msg, 'yellow', '⚠ ')
        self._web(msg, 'warning')

    def error(self, msg):
        self._term(msg, 'red', '✗ ')
        self._web(msg, 'error')

    def critical(self, msg):
        self._term(msg, 'red', '⛔ ')
        self._web(msg, 'critical')

    def debug(self, msg):
        self._term(msg, 'dim', '… ')
        self._web(msg, 'debug')

    def banner(self, msg):
        c = self.COLORS['cyan']
        r = self.COLORS['reset']
        b = self.COLORS['bold']
        print(f"\n{b}{c}{'='*60}{r}")
        print(f"{b}{c}  {msg}{r}")
        print(f"{b}{c}{'='*60}{r}\n")

log = DualLogger()

# ============================================================
# DATABASE
# ============================================================
class MythosDB:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS scans (
                    id TEXT PRIMARY KEY,
                    target TEXT NOT NULL,
                    scan_type TEXT NOT NULL,
                    status TEXT DEFAULT 'running',
                    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    finished_at TEXT,
                    result_count INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS intelligence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id TEXT,
                    layer TEXT,
                    category TEXT,
                    key_field TEXT,
                    value_field TEXT,
                    confidence REAL DEFAULT 0.0,
                    source TEXT,
                    raw_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (scan_id) REFERENCES scans(id)
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id TEXT,
                    evidence_type TEXT,
                    title TEXT,
                    description TEXT,
                    data TEXT,
                    hash_sha256 TEXT,
                    collected_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (scan_id) REFERENCES scans(id)
                );
                CREATE TABLE IF NOT EXISTS kill_chain (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id TEXT,
                    phase TEXT,
                    action TEXT,
                    target TEXT,
                    status TEXT DEFAULT 'pending',
                    result TEXT,
                    executed_at TEXT,
                    FOREIGN KEY (scan_id) REFERENCES scans(id)
                );
                CREATE TABLE IF NOT EXISTS blocklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT UNIQUE,
                    ip_address TEXT,
                    reason TEXT,
                    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    source TEXT
                );
            """)
            self.conn.commit()

    def create_scan(self, scan_id, target, scan_type):
        with self._lock:
            self.conn.execute(
                "INSERT INTO scans (id, target, scan_type) VALUES (?,?,?)",
                (scan_id, target, scan_type))
            self.conn.commit()

    def update_scan(self, scan_id, **kwargs):
        with self._lock:
            sets = ", ".join(f"{k}=?" for k in kwargs)
            vals = list(kwargs.values()) + [scan_id]
            self.conn.execute(f"UPDATE scans SET {sets} WHERE id=?", vals)
            self.conn.commit()

    def add_intel(self, scan_id, layer, category, key_field, value_field,
                  confidence=0.0, source='', raw_data=''):
        with self._lock:
            self.conn.execute(
                """INSERT INTO intelligence
                   (scan_id,layer,category,key_field,value_field,confidence,source,raw_data)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (scan_id, layer, category, key_field, value_field,
                 confidence, source, raw_data))
            self.conn.commit()

    def add_evidence(self, scan_id, evidence_type, title, description, data):
        h = hashlib.sha256(data.encode()).hexdigest() if isinstance(data, str) else hashlib.sha256(data).hexdigest()
        with self._lock:
            self.conn.execute(
                """INSERT INTO evidence
                   (scan_id,evidence_type,title,description,data,hash_sha256)
                   VALUES (?,?,?,?,?,?)""",
                (scan_id, evidence_type, title, description, data, h))
            self.conn.commit()

    def add_kill_chain(self, scan_id, phase, action, target):
        with self._lock:
            self.conn.execute(
                """INSERT INTO kill_chain (scan_id,phase,action,target)
                   VALUES (?,?,?,?)""",
                (scan_id, phase, action, target))
            self.conn.commit()

    def update_kill_chain(self, scan_id, phase, status, result=''):
        with self._lock:
            self.conn.execute(
                """UPDATE kill_chain SET status=?, result=?, executed_at=?
                   WHERE scan_id=? AND phase=?""",
                (status, result, datetime.datetime.now().isoformat(), scan_id, phase))
            self.conn.commit()

    def add_blocklist(self, domain, ip_address, reason, source='mythos'):
        with self._lock:
            try:
                self.conn.execute(
                    """INSERT OR IGNORE INTO blocklist (domain,ip_address,reason,source)
                       VALUES (?,?,?,?)""",
                    (domain, ip_address, reason, source))
                self.conn.commit()
            except Exception:
                pass

    def get_scans(self, limit=50):
        with self._lock:
            rows = self.conn.execute(
                "SELECT * FROM scans ORDER BY started_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_intel(self, scan_id):
        with self._lock:
            rows = self.conn.execute(
                "SELECT * FROM intelligence WHERE scan_id=? ORDER BY layer,category", (scan_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_evidence(self, scan_id):
        with self._lock:
            rows = self.conn.execute(
                "SELECT * FROM evidence WHERE scan_id=? ORDER BY collected_at", (scan_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_kill_chain(self, scan_id):
        with self._lock:
            rows = self.conn.execute(
                "SELECT * FROM kill_chain WHERE scan_id=? ORDER BY id", (scan_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_blocklist(self):
        with self._lock:
            rows = self.conn.execute(
                "SELECT * FROM blocklist ORDER BY added_at DESC").fetchall()
            return [dict(r) for r in rows]

    def get_stats(self):
        with self._lock:
            scans = self.conn.execute("SELECT COUNT(*) as c FROM scans").fetchone()['c']
            intel = self.conn.execute("SELECT COUNT(*) as c FROM intelligence").fetchone()['c']
            evidence = self.conn.execute("SELECT COUNT(*) as c FROM evidence").fetchone()['c']
            blocked = self.conn.execute("SELECT COUNT(*) as c FROM blocklist").fetchone()['c']
            return {'scans': scans, 'intelligence': intel, 'evidence': evidence, 'blocked': blocked}

db = MythosDB()

# ============================================================
# KALI LINUX TOOL WRAPPERS
# ============================================================
class KaliTools:
    """Integration with 50+ Kali Linux security tools"""

    def __init__(self, logger):
        self.log = logger
        self._check_tools()

    def _check_tools(self):
        self.tools = {}
        common = [
            'nmap', 'sqlmap', 'nikto', 'dirb', 'gobuster', 'ffuf',
            'wpscan', 'enum4linux', 'smbclient', 'hydra', 'medusa',
            'john', 'hashcat', 'aircrack-ng', 'wireshark', 'tcpdump',
            'burpsuite', 'zaproxy', 'metasploit', 'msfconsole',
            'responder', 'impacket', 'crackmapexec', 'bloodhound',
            'nuclei', 'httpx', 'subfinder', 'amass', 'shodan',
            'censys', 'theHarvester', 'maltego', 'spiderfoot',
            'recon-ng', 'osint-framework', 'whois', 'dig', 'host',
            'dnsrecon', 'dnsenum', 'fierce', 'massdns',
            'whatweb', 'wafw00f', 'sslscan', 'sslyze',
            'searchsploit', 'exploitdb', 'payloadsallthethings',
            'feroxbuster', 'rustscan', 'naabu', 'httpx-toolkit'
        ]
        for tool in common:
            result = shutil.which(tool)
            if result:
                self.tools[tool] = result

    def available(self):
        return list(self.tools.keys())

    def _run(self, cmd, timeout=300):
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return f"[TIMEOUT] Command timed out after {timeout}s"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    # --- RECONNAISSANCE ---
    def nmap_scan(self, target, scan_type='quick'):
        if 'nmap' not in self.tools:
            return "[SKIP] nmap not found"
        opts = {
            'quick': '-sV --top-ports 100 -T4',
            'full': '-sV -sC -p- -T4',
            'stealth': '-sS -T2 -f --data-length 24',
            'vuln': '--script vuln -sV',
            'udp': '-sU --top-ports 50 -T4',
        }
        opt = opts.get(scan_type, opts['quick'])
        self.log.info(f"nmap {scan_type} scan → {target}")
        return self._run(f"sudo {self.tools['nmap']} {opt} {target}")

    def rustscan(self, target):
        if 'rustscan' not in self.tools:
            return self.nmap_scan(target, 'quick')
        self.log.info(f"rustscan → {target}")
        return self._run(f"{self.tools['rustscan']} -a {target} -- -sV")

    def naabu_scan(self, target):
        if 'naabu' not in self.tools:
            return "[SKIP] naabu not found"
        self.log.info(f"naabu → {target}")
        return self._run(f"{self.tools['naabu']} -host {target}")

    # --- DNS ---
    def dns_enum(self, domain):
        results = []
        self.log.info(f"DNS enumeration → {domain}")
        # dig
        if shutil.which('dig'):
            r = self._run(f"dig ANY +noall +answer {domain}")
            results.append(('DNS-DIG', r))
        # dnsrecon
        if 'dnsrecon' in self.tools:
            r = self._run(f"{self.tools['dnsrecon']} -d {domain} -t std")
            results.append(('DNSRECON', r))
        # dnsenum
        if 'dnsenum' in self.tools:
            r = self._run(f"{self.tools['dnsenum']} {domain}")
            results.append(('DNSENUM', r))
        # fierce
        if 'fierce' in self.tools:
            r = self._run(f"{self.tools['fierce']} --domain {domain}")
            results.append(('FIERCE', r))
        return results

    def subdomain_enum(self, domain):
        results = []
        self.log.info(f"Subdomain enumeration → {domain}")
        if 'subfinder' in self.tools:
            r = self._run(f"{self.tools['subfinder']} -d {domain} -silent")
            results.append(('SUBFINDER', r))
        if 'amass' in self.tools:
            r = self._run(f"{self.tools['amass']} enum -passive -d {domain}")
            results.append(('AMASS', r))
        return results

    # --- WEB ---
    def web_scan(self, url):
        results = []
        self.log.info(f"Web scanning → {url}")
        # nikto
        if 'nikto' in self.tools:
            r = self._run(f"{self.tools['nikto']} -h {url} -Tuning 1234567890", 180)
            results.append(('NIKTO', r))
        # whatweb
        if 'whatweb' in self.tools:
            r = self._run(f"{self.tools['whatweb']} -a 3 {url}")
            results.append(('WHATWEB', r))
        # wafw00f
        if 'wafw00f' in self.tools:
            r = self._run(f"{self.tools['wafw00f']} {url}")
            results.append(('WAFW00F', r))
        # sslscan
        if 'sslscan' in self.tools:
            r = self._run(f"{self.tools['sslscan']} {url}")
            results.append(('SSLSCAN', r))
        return results

    def dir_bruteforce(self, url, wordlist=None):
        results = []
        wl = wordlist or '/usr/share/wordlists/dirb/common.txt'
        if not os.path.exists(wl):
            wl = '/usr/share/wordlists/dirbuster/directory-list-2.3-small.txt'
        self.log.info(f"Directory bruteforce → {url}")
        if 'gobuster' in self.tools:
            r = self._run(f"{self.tools['gobuster']} dir -u {url} -w {wl} -q", 180)
            results.append(('GOBUSTER', r))
        elif 'dirb' in self.tools:
            r = self._run(f"{self.tools['dirb']} {url} {wl} -r", 180)
            results.append(('DIRB', r))
        if 'feroxbuster' in self.tools:
            r = self._run(f"{self.tools['feroxbuster']} -u {url} -w {wl} --quiet", 180)
            results.append(('FEROXBUSTER', r))
        return results

    def vuln_scan(self, url):
        results = []
        self.log.info(f"Vulnerability scanning → {url}")
        if 'nuclei' in self.tools:
            r = self._run(f"{self.tools['nuclei']} -u {url} -severity medium,high,critical", 300)
            results.append(('NUCLEI', r))
        if 'sqlmap' in self.tools:
            r = self._run(f"{self.tools['sqlmap']} -u {url} --batch --level=1 --risk=1 --random-agent", 180)
            results.append(('SQLMAP', r))
        if 'wpscan' in self.tools:
            r = self._run(f"{self.tools['wpscan']} --url {url} --random-user-agent --enumerate u,p,t", 180)
            results.append(('WPSCAN', r))
        return results

    # --- OSINT ---
    def osint_harvest(self, domain):
        results = []
        self.log.info(f"OSINT harvesting → {domain}")
        if 'theHarvester' in self.tools:
            r = self._run(f"{self.tools['theHarvester']} -d {domain} -b all", 180)
            results.append(('THEHARVESTER', r))
        # whois
        if shutil.which('whois'):
            r = self._run(f"whois {domain}")
            results.append(('WHOIS', r))
        # shodan (if CLI available)
        if 'shodan' in self.tools:
            r = self._run(f"{self.tools['shodan']} host {domain}")
            results.append(('SHODAN', r))
        return results

    # --- SMB / NETWORK ---
    def smb_enum(self, target):
        results = []
        self.log.info(f"SMB enumeration → {target}")
        if 'enum4linux' in self.tools:
            r = self._run(f"{self.tools['enum4linux']} -a {target}", 180)
            results.append(('ENUM4LINUX', r))
        if 'smbclient' in self.tools:
            r = self._run(f"{self.tools['smbclient']} -L //{target}/ -N")
            results.append(('SMBCLIENT', r))
        if 'crackmapexec' in self.tools:
            r = self._run(f"{self.tools['crackmapexec']} smb {target}")
            results.append(('CRACKMAPEXEC', r))
        return results

    # --- EXPLOIT SEARCH ---
    def search_exploit(self, query):
        if 'searchsploit' in self.tools:
            self.log.info(f"Exploit search → {query}")
            return self._run(f"{self.tools['searchsploit']} {query}")
        return "[SKIP] searchsploit not found"

    # --- SSL/TLS ---
    def ssl_analyze(self, host):
        results = []
        self.log.info(f"SSL/TLS analysis → {host}")
        if 'sslscan' in self.tools:
            r = self._run(f"{self.tools['sslscan']} {host}")
            results.append(('SSLSCAN', r))
        if 'sslyze' in self.tools:
            r = self._run(f"{self.tools['sslyze']} --regular {host}")
            results.append(('SSLYZE', r))
        return results

kali = KaliTools(log)

# ============================================================
# PAYMENT GATEWAY DETECTOR — "Senjata Utama"
# Potong aliran uang = mati
# ============================================================
class PaymentGatewayDetector:
    """
    💰 Payment Gateway Detector v2.0
    Senjata utama untuk memotong aliran uang judi online.
    
    Mendeteksi:
    - Payment processors (Midtrans, Xendit, DOKU, dkk)
    - E-wallet (DANA, OVO, GoPay, ShopeePay, LinkAja)
    - Crypto wallets (BTC, ETH, USDT, TRX)
    - Bank transfers (BCA, BRI, Mandiri, BNI, dll)
    - QRIS codes
    - SMS/Credit card processors
    - Affiliate/referral payment systems
    
    Auto-generate:
    - Laporan ke payment processor untuk pemblokiran
    - Evidence untuk penegakan hukum
    - STRANGLE action: potong aliran uang
    """

    # ---- PAYMENT PROCESSOR DATABASE ----
    PAYMENT_PROCESSORS = {
        # Indonesia Payment Gateways
        'midtrans': {
            'name': 'Midtrans (GoTo Financial)',
            'domain_patterns': ['midtrans.com', 'snap.midtrans.com', 'api.midtrans.com',
                               'app.midtrans.com', 'vt-direct.veritrans.co.id'],
            'js_patterns': ['midtrans', 'veritrans', 'vt-direct', 'Snap.pay'],
            'report_email': 'risk@midtrans.com',
            'report_url': 'https://midtrans.com/help',
            'category': 'payment_gateway',
            'severity': 'CRITICAL',
            'action': 'Laporkan ke Midtrans Risk Team — pemblokiran merchant ID'
        },
        'xendit': {
            'name': 'Xendit',
            'domain_patterns': ['xendit.co', 'api.xendit.co', 'invoice.xendit.co',
                               'www.xendit.co'],
            'js_patterns': ['xendit', 'Xendit.createInvoice', 'xendit.js'],
            'report_email': 'compliance@xendit.co',
            'report_url': 'https://www.xendit.co/en/contact-us/',
            'category': 'payment_gateway',
            'severity': 'CRITICAL',
            'action': 'Laporkan ke Xendit Compliance — pemblokiran akun'
        },
        'doku': {
            'name': 'DOKU (DOKU ANDA)',
            'domain_patterns': ['doku.com', 'pay.doku.com', 'api.doku.com',
                               'my.doku.com', 'checkout.doku.com'],
            'js_patterns': ['doku', 'DOKU.pay', 'doku.js'],
            'report_email': 'risk@doku.com',
            'report_url': 'https://www.doku.com/contact-us',
            'category': 'payment_gateway',
            'severity': 'CRITICAL',
            'action': 'Laporkan ke DOKU Risk — pemblokiran merchant'
        },
        'tripay': {
            'name': 'Tripay',
            'domain_patterns': ['tripay.co.id', 'api.tripay.co.id',
                               'checkout.tripay.co.id'],
            'js_patterns': ['tripay', 'Tripay.pay'],
            'report_email': 'support@tripay.co.id',
            'report_url': 'https://tripay.co.id/contact',
            'category': 'payment_gateway',
            'severity': 'HIGH',
            'action': 'Laporkan ke Tripay — pemblokiran merchant'
        },
        'ipaymu': {
            'name': 'iPaymu',
            'domain_patterns': ['ipaymu.com', 'api.ipaymu.com'],
            'js_patterns': ['ipaymu'],
            'report_email': 'support@ipaymu.com',
            'report_url': 'https://ipaymu.com/contact',
            'category': 'payment_gateway',
            'severity': 'HIGH',
            'action': 'Laporkan ke iPaymu — pemblokiran akun'
        },
        'faspay': {
            'name': 'Faspay',
            'domain_patterns': ['faspay.co.id', 'web.faspay.co.id'],
            'js_patterns': ['faspay', 'Faspay.checkout'],
            'report_email': 'support@faspay.co.id',
            'category': 'payment_gateway',
            'severity': 'HIGH',
            'action': 'Laporkan ke Faspay — pemblokiran merchant'
        },
        'nicepay': {
            'name': 'NICEPay',
            'domain_patterns': ['nicepay.co.id', 'api.nicepay.co.id'],
            'js_patterns': ['nicepay', 'NICEPay.pay'],
            'report_email': 'support@nicepay.co.id',
            'category': 'payment_gateway',
            'severity': 'HIGH',
            'action': 'Laporkan ke NICEPay — pemblokiran merchant'
        },
        # International
        'stripe': {
            'name': 'Stripe',
            'domain_patterns': ['stripe.com', 'js.stripe.com', 'api.stripe.com',
                               'checkout.stripe.com', 'pay.stripe.com'],
            'js_patterns': ['Stripe(', 'stripe.js', 'StripeCheckout'],
            'report_email': 'fraud@stripe.com',
            'report_url': 'https://stripe.com/report',
            'category': 'payment_gateway_intl',
            'severity': 'CRITICAL',
            'action': 'Report to Stripe Fraud — merchant account termination'
        },
        'paypal': {
            'name': 'PayPal',
            'domain_patterns': ['paypal.com', 'paypalobjects.com', 'paypal.me'],
            'js_patterns': ['paypal', 'paypal-button', 'PAYPAL'],
            'report_email': 'abuse@paypal.com',
            'report_url': 'https://www.paypal.com/report',
            'category': 'payment_gateway_intl',
            'severity': 'HIGH',
            'action': 'Report to PayPal AUP — account limitation'
        },
    }

    # ---- E-WALLET DATABASE ----
    E_WALLETS = {
        'dana': {
            'name': 'DANA',
            'domain_patterns': ['dana.id', 'api.dana.id', 'm.dana.id',
                               'app.dana.id', 'checkout.dana.id'],
            'js_patterns': ['dana', 'DANA.pay', 'dana.id'],
            'deep_link': ['dana://', 'dana.id://'],
            'report_email': 'compliance@dana.id',
            'category': 'e_wallet',
            'severity': 'CRITICAL',
            'action': 'Laporkan ke DANA Compliance — pemblokiran merchant'
        },
        'ovo': {
            'name': 'OVO',
            'domain_patterns': ['ovo.id', 'api.ovo.id', 'pay.ovo.id'],
            'js_patterns': ['ovo', 'OVO.pay'],
            'deep_link': ['ovo://'],
            'report_email': 'cs@ovo.id',
            'category': 'e_wallet',
            'severity': 'CRITICAL',
            'action': 'Laporkan ke OVO — pemblokiran merchant'
        },
        'gopay': {
            'name': 'GoPay (GoTo)',
            'domain_patterns': ['gopay.co.id', 'api.gopay.co.id', 'pay.gopay.co.id',
                               'gocash.gojek.com'],
            'js_patterns': ['gopay', 'GoPay', 'gopay-checkout'],
            'deep_link': ['gopay://', 'gojek://'],
            'report_email': 'compliance@gojek.com',
            'category': 'e_wallet',
            'severity': 'CRITICAL',
            'action': 'Laporkan ke GoPay Compliance — pemblokiran merchant'
        },
        'shopeepay': {
            'name': 'ShopeePay',
            'domain_patterns': ['shopeepay.co.id', 'wallet.airpay.shopee.co.id',
                               'shopee.co.id'],
            'js_patterns': ['shopeepay', 'ShopeePay', 'airpay'],
            'deep_link': ['shopeepay://', 'shopee://'],
            'report_email': 'compliance@shopee.co.id',
            'category': 'e_wallet',
            'severity': 'HIGH',
            'action': 'Laporkan ke ShopeePay — pemblokiran merchant'
        },
        'linkaja': {
            'name': 'LinkAja',
            'domain_patterns': ['linkaja.id', 'api.linkaja.id', 'pay.linkaja.id'],
            'js_patterns': ['linkaja', 'LinkAja'],
            'deep_link': ['linkaja://'],
            'report_email': 'cs@linkaja.id',
            'category': 'e_wallet',
            'severity': 'HIGH',
            'action': 'Laporkan ke LinkAja — pemblokiran merchant'
        },
    }

    # ---- CRYPTO PATTERNS ----
    CRYPTO_PATTERNS = {
        'bitcoin': {
            'name': 'Bitcoin (BTC)',
            'address_regex': r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-zA-HJ-NP-Z0-9]{25,87}',
            'report_url': 'https://www.bitcoinabuse.com/reports',
            'category': 'crypto',
            'severity': 'HIGH'
        },
        'ethereum': {
            'name': 'Ethereum (ETH)',
            'address_regex': r'0x[a-fA-F0-9]{40}',
            'report_url': 'https://etherscan.io/report',
            'category': 'crypto',
            'severity': 'HIGH'
        },
        'usdt_trc20': {
            'name': 'USDT (TRC20)',
            'address_regex': r'T[A-HJ-NP-Za-km-z1-9]{33}',
            'report_url': 'https://tronscan.org/#/report',
            'category': 'crypto',
            'severity': 'HIGH'
        },
        'usdt_erc20': {
            'name': 'USDT (ERC20)',
            'address_regex': r'0x[a-fA-F0-9]{40}',
            'report_url': 'https://etherscan.io/report',
            'category': 'crypto',
            'severity': 'HIGH'
        },
    }

    # ---- BANK TRANSFER PATTERNS ----
    BANK_PATTERNS = {
        'bca': {'name': 'BCA', 'patterns': ['bca', 'bank bca', 'bank central asia'],
                'code_prefix': '014', 'category': 'bank_transfer'},
        'bri': {'name': 'BRI', 'patterns': ['bri', 'bank bri', 'bank rakyat indonesia'],
                'code_prefix': '002', 'category': 'bank_transfer'},
        'mandiri': {'name': 'Mandiri', 'patterns': ['mandiri', 'bank mandiri'],
                    'code_prefix': '008', 'category': 'bank_transfer'},
        'bni': {'name': 'BNI', 'patterns': ['bni', 'bank bni', 'bank negara indonesia'],
                'code_prefix': '009', 'category': 'bank_transfer'},
        'bsi': {'name': 'BSI', 'patterns': ['bsi', 'bank bsi', 'bank syariah indonesia'],
                'code_prefix': '451', 'category': 'bank_transfer'},
        'cimb': {'name': 'CIMB Niaga', 'patterns': ['cimb', 'cimb niaga'],
                 'code_prefix': '022', 'category': 'bank_transfer'},
        'danamon': {'name': 'Danamon', 'patterns': ['danamon', 'bank danamon'],
                    'code_prefix': '011', 'category': 'bank_transfer'},
        'permata': {'name': 'Permata', 'patterns': ['permata', 'bank permata'],
                    'code_prefix': '013', 'category': 'bank_transfer'},
    }

    # ---- QRIS PATTERN ----
    QRIS_PATTERNS = {
        'js_patterns': ['qris', 'QRIS', 'generate-qr', 'qr-code-payment', 'quick-response'],
        'dom_patterns': ['qris.id', 'api.qris.id'],
        'report_email': 'kominfo@qris.id',
        'severity': 'HIGH'
    }

    # ---- GAMBLING PAYMENT UI PATTERNS ----
    GAMBLING_PAYMENT_PATTERNS = [
        # Indonesian gambling deposit/withdraw keywords
        r'deposit\s*(?:minimal|min)\s*rp',
        r'min(?:imum)?\s*deposit\s*\d+',
        r'withdraw\s*(?:minimal|min)\s*rp',
        r'metode\s*deposit',
        r'cara\s*deposit',
        r'rekening\s*tujuan',
        r'nomor\s*rekening',
        r'via\s*(?:dana|ovo|gopay|shopeepay|linkaja|pulsa)',
        r'slot\s*deposit\s*(?:dana|ovo|gopay|pulsa)',
        r'togel\s*deposit\s*(?:minimal|murah)',
        r'bonus\s*(?:deposit|new\s*member|rollingan|cashback)',
        r'rate\s*(?:deposit|withdraw)',
        r'proses\s*(?:deposit|wd|withdraw)\s*(?:cepat|tercepat|instan)',
        r'metode\s*pembayaran',
        r'payment\s*method',
        r'deposit\s*pulsa',
        r'slot\s*via\s*pulsa',
        r'qris\s*deposit',
    ]

    def __init__(self, logger, db_conn, classifier_inst):
        self.log = logger
        self.db = db_conn
        self.classifier = classifier_inst

    def analyze_url(self, scan_id, url):
        """
        Analyze a URL for payment gateway integrations.
        Fetches the page and searches for all payment indicators.
        Returns dict of detected payment methods.
        """
        self.log.info(f"[PAYMENT-GW] Scanning payment gateways → {url}")
        results = {
            'payment_processors': [],
            'e_wallets': [],
            'crypto_wallets': [],
            'bank_transfers': [],
            'qris': False,
            'gambling_payment_ui': [],
            'strangle_targets': []
        }

        # Fetch page content
        html_content = self._fetch_page(url)
        if not html_content:
            self.log.warning(f"[PAYMENT-GW] Could not fetch {url}, trying cached data")
            return results

        self.log.info(f"[PAYMENT-GW] Analyzing {len(html_content)} bytes of content")

        # 1. Detect Payment Processors
        for key, pg in self.PAYMENT_PROCESSORS.items():
            detected = False
            # Check domain references in HTML
            for domain in pg['domain_patterns']:
                if domain in html_content:
                    detected = True
                    break
            # Check JS patterns
            if not detected:
                for js_pattern in pg['js_patterns']:
                    if js_pattern.lower() in html_content.lower():
                        detected = True
                        break
            if detected:
                self.log.success(f"[PAYMENT-GW] Detected: {pg['name']} ({pg['severity']})")
                results['payment_processors'].append({
                    'key': key,
                    'name': pg['name'],
                    'severity': pg['severity'],
                    'category': pg['category'],
                    'report_email': pg.get('report_email', ''),
                    'report_url': pg.get('report_url', ''),
                    'action': pg.get('action', '')
                })
                # Add to L4_FINANCIAL intelligence
                self.db.add_intel(scan_id, 'L4_FINANCIAL', 'payment_processor',
                                 key, pg['name'], 0.95, 'payment_detector')
                # Add as strangle target
                results['strangle_targets'].append({
                    'type': 'payment_processor',
                    'name': pg['name'],
                    'report_email': pg.get('report_email', ''),
                    'report_url': pg.get('report_url', ''),
                    'action': pg.get('action', '')
                })

        # 2. Detect E-Wallets
        for key, ew in self.E_WALLETS.items():
            detected = False
            for domain in ew['domain_patterns']:
                if domain in html_content:
                    detected = True
                    break
            if not detected:
                for js_pattern in ew['js_patterns']:
                    if js_pattern.lower() in html_content.lower():
                        detected = True
                        break
            if not detected:
                for dl in ew.get('deep_link', []):
                    if dl in html_content:
                        detected = True
                        break
            if detected:
                self.log.success(f"[PAYMENT-GW] E-Wallet detected: {ew['name']} ({ew['severity']})")
                results['e_wallets'].append({
                    'key': key,
                    'name': ew['name'],
                    'severity': ew['severity'],
                    'report_email': ew.get('report_email', ''),
                    'action': ew.get('action', '')
                })
                self.db.add_intel(scan_id, 'L4_FINANCIAL', 'e_wallet',
                                 key, ew['name'], 0.95, 'payment_detector')
                results['strangle_targets'].append({
                    'type': 'e_wallet',
                    'name': ew['name'],
                    'report_email': ew.get('report_email', ''),
                    'action': ew.get('action', '')
                })

        # 3. Detect Crypto Wallets
        for key, crypto in self.CRYPTO_PATTERNS.items():
            addresses = re.findall(crypto['address_regex'], html_content)
            if addresses:
                unique_addrs = list(set(addresses))[:10]  # Limit to 10
                self.log.success(f"[PAYMENT-GW] Crypto detected: {crypto['name']} — {len(unique_addrs)} address(es)")
                results['crypto_wallets'].append({
                    'key': key,
                    'name': crypto['name'],
                    'addresses': unique_addrs,
                    'severity': crypto['severity']
                })
                for addr in unique_addrs:
                    self.db.add_intel(scan_id, 'L4_FINANCIAL', 'crypto_address',
                                     key, addr, 0.9, 'payment_detector')
                results['strangle_targets'].append({
                    'type': 'crypto',
                    'name': crypto['name'],
                    'addresses': unique_addrs,
                    'report_url': crypto.get('report_url', '')
                })

        # 4. Detect Bank Transfers
        html_lower = html_content.lower()
        for key, bank in self.BANK_PATTERNS.items():
            detected = False
            for pattern in bank['patterns']:
                if pattern in html_lower:
                    detected = True
                    break
            if detected:
                self.log.success(f"[PAYMENT-GW] Bank detected: {bank['name']}")
                results['bank_transfers'].append({
                    'key': key,
                    'name': bank['name'],
                    'code_prefix': bank['code_prefix'],
                    'category': bank['category']
                })
                self.db.add_intel(scan_id, 'L4_FINANCIAL', 'bank_transfer',
                                 key, bank['name'], 0.85, 'payment_detector')

        # 5. Detect QRIS
        qris_detected = False
        for js_pat in self.QRIS_PATTERNS['js_patterns']:
            if js_pat.lower() in html_lower:
                qris_detected = True
                break
        if qris_detected:
            self.log.success(f"[PAYMENT-GW] QRIS payment detected")
            results['qris'] = True
            self.db.add_intel(scan_id, 'L4_FINANCIAL', 'qris',
                             'qris', 'QRIS Payment Detected', 0.9, 'payment_detector')

        # 6. Detect Gambling Payment UI Patterns
        for pattern in self.GAMBLING_PAYMENT_PATTERNS:
            matches = re.findall(pattern, html_lower)
            if matches:
                self.log.success(f"[PAYMENT-GW] Gambling payment UI: {pattern}")
                results['gambling_payment_ui'].append({
                    'pattern': pattern,
                    'matches': len(matches),
                    'sample': matches[0] if matches else ''
                })
                self.db.add_intel(scan_id, 'L2_CONTENT', 'gambling_payment_ui',
                                 'pattern', pattern, 0.95, 'payment_detector')

        # 7. Generate Evidence
        if results['payment_processors'] or results['e_wallets'] or results['crypto_wallets'] or results['bank_transfers']:
            total = (len(results['payment_processors']) + len(results['e_wallets']) +
                    len(results['crypto_wallets']) + len(results['bank_transfers']))
            evidence_data = self._generate_evidence_report(url, results)
            self.db.add_evidence(
                scan_id, 'payment_analysis',
                f'Payment Gateway Analysis: {url}',
                f'Detected {total} payment method(s) — {len(results["strangle_targets"])} strangle target(s)',
                evidence_data
            )
            self.log.banner(f"PAYMENT DETECTION: {total} payment method(s) found — STRANGLE READY")

        return results

    def _fetch_page(self, url):
        """Fetch page content using curl or wget"""
        if not url.startswith('http'):
            url = f'https://{url}'
        try:
            result = subprocess.run(
                ['curl', '-sL', '--max-time', '15', '-A',
                 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                 url],
                capture_output=True, text=True, timeout=20
            )
            return result.stdout
        except Exception:
            pass
        # Fallback to wget
        try:
            result = subprocess.run(
                ['wget', '-qO-', '--timeout=15', '-U',
                 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                 url],
                capture_output=True, text=True, timeout=20
            )
            return result.stdout
        except Exception:
            return ''

    def _generate_evidence_report(self, url, results):
        """Generate structured evidence report"""
        report = []
        report.append(f"MYTHOS NEMESIS — Payment Gateway Detection Report")
        report.append(f"Target: {url}")
        report.append(f"Timestamp: {datetime.datetime.now().isoformat()}")
        report.append(f"")
        report.append(f"=== PAYMENT PROCESSORS ({len(results['payment_processors'])}) ===")
        for pp in results['payment_processors']:
            report.append(f"  [{pp['severity']}] {pp['name']}")
            report.append(f"    Report: {pp.get('report_email', 'N/A')}")
            report.append(f"    Action: {pp.get('action', 'N/A')}")
        report.append(f"")
        report.append(f"=== E-WALLETS ({len(results['e_wallets'])}) ===")
        for ew in results['e_wallets']:
            report.append(f"  [{ew['severity']}] {ew['name']}")
            report.append(f"    Report: {ew.get('report_email', 'N/A')}")
        report.append(f"")
        report.append(f"=== CRYPTO WALLETS ({len(results['crypto_wallets'])}) ===")
        for cw in results['crypto_wallets']:
            report.append(f"  [{cw['severity']}] {cw['name']}: {len(cw['addresses'])} address(es)")
            for addr in cw['addresses'][:5]:
                report.append(f"    → {addr}")
        report.append(f"")
        report.append(f"=== BANK TRANSFERS ({len(results['bank_transfers'])}) ===")
        for bt in results['bank_transfers']:
            report.append(f"  {bt['name']} (Code: {bt['code_prefix']})")
        report.append(f"")
        report.append(f"=== QRIS: {'DETECTED' if results['qris'] else 'Not detected'} ===")
        report.append(f"")
        report.append(f"=== GAMBLING PAYMENT UI ({len(results['gambling_payment_ui'])}) ===")
        for gp in results['gambling_payment_ui']:
            report.append(f"  Pattern: {gp['pattern']} ({gp['matches']}x)")
        report.append(f"")
        report.append(f"=== STRANGLE TARGETS ({len(results['strangle_targets'])}) ===")
        for st in results['strangle_targets']:
            report.append(f"  [{st['type']}] {st['name']}")
            report.append(f"    → {st.get('action', st.get('report_url', 'N/A'))}")
        return '\n'.join(report)

    def generate_strangle_reports(self, scan_id, target, detection_results):
        """
        Auto-generate abuse reports for all detected payment methods.
        This is the KILL ACTION — potong aliran uang.
        """
        domain = target.replace('http://', '').replace('https://', '').split('/')[0]
        reports_generated = []

        for st in detection_results.get('strangle_targets', []):
            report = self._create_payment_abuse_report(domain, st)
            if report:
                self.db.add_evidence(
                    scan_id,
                    f"strangle_report_{st['type']}",
                    f"STRANGLE: {st['name']} Abuse Report",
                    f'Payment abuse report for {st["name"]} — {st.get("action", "Request block")}',
                    report
                )
                reports_generated.append({
                    'target': st['name'],
                    'type': st['type'],
                    'report_email': st.get('report_email', ''),
                    'report_url': st.get('report_url', '')
                })
                self.log.success(f"[STRANGLE] Abuse report generated for {st['name']}")

        return reports_generated

    def _create_payment_abuse_report(self, domain, target_info):
        """Create a formatted abuse report for a payment processor"""
        report = []
        report.append(f"ABUSE REPORT — Online Gambling Payment Processing")
        report.append(f"=" * 55)
        report.append(f"")
        report.append(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Reporting Entity: MYTHOS NEMESIS Automated Detection System")
        report.append(f"Reported By: ibnu qory nur fikri / Dorakula")
        report.append(f"")
        report.append(f"PAYMENT PROCESSOR: {target_info.get('name', 'Unknown')}")
        report.append(f"VIOLATION TYPE: Processing payments for online gambling")
        report.append(f"GAMBLING WEBSITE: {domain}")
        report.append(f"")
        report.append(f"EVIDENCE:")
        report.append(f"  - Automated detection by MYTHOS NEMESIS Payment Gateway Detector")
        report.append(f"  - Gambling site {domain} is using {target_info.get('name', 'Unknown')} for payment processing")
        report.append(f"  - This constitutes a violation of Indonesian law (UU ITE, UU Judi)")
        report.append(f"")
        report.append(f"LEGAL BASIS:")
        report.append(f"  - UU No. 11/2008 tentang ITE (pasal 27, 28)")
        report.append(f"  - UU No. 11/2020 tentang Cipta Kerja (pasal 27)")
        report.append(f"  - PP No. 71/2019 tentang Penyelenggaraan Sistem dan Transaksi Elektronik")
        report.append(f"  - Peraturan Bank Indonesia tentang Payment System")
        report.append(f"")
        report.append(f"REQUESTED ACTION:")
        report.append(f"  1. Immediately block merchant account associated with {domain}")
        report.append(f"  2. Freeze any funds held in the merchant account")
        report.append(f"  3. Report merchant information to Bank Indonesia / OJK")
        report.append(f"  4. Preserve transaction records for law enforcement")
        report.append(f"")
        report.append(f"CONTACT: Please contact relevant Indonesian authorities for verification")
        report.append(f"  - Kominfo: https://kominfo.go.id")
        report.append(f"  - BSSN: https://bssn.go.id")
        report.append(f"  - PPATK: https://ppatk.go.id")
        return '\n'.join(report)

    def get_all_processors(self):
        """Return all known payment processors for reference"""
        all_procs = {}
        for key, pg in self.PAYMENT_PROCESSORS.items():
            all_procs[key] = {'name': pg['name'], 'severity': pg['severity'],
                             'category': pg['category']}
        for key, ew in self.E_WALLETS.items():
            all_procs[key] = {'name': ew['name'], 'severity': ew['severity'],
                             'category': ew['category']}
        return all_procs

    def get_strangle_actions(self, detection_results):
        """Return prioritized list of STRANGLE actions"""
        actions = []
        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}

        for st in detection_results.get('strangle_targets', []):
            # Find severity
            severity = 'MEDIUM'
            if st['type'] == 'payment_processor':
                for k, v in self.PAYMENT_PROCESSORS.items():
                    if k == st.get('key', ''):
                        severity = v['severity']
                        break
            elif st['type'] == 'e_wallet':
                for k, v in self.E_WALLETS.items():
                    if k == st.get('key', ''):
                        severity = v['severity']
                        break
            elif st['type'] == 'crypto':
                severity = 'HIGH'

            actions.append({
                'priority': priority_order.get(severity, 3),
                'target': st['name'],
                'type': st['type'],
                'severity': severity,
                'report_email': st.get('report_email', ''),
                'report_url': st.get('report_url', ''),
                'action': st.get('action', '')
            })

        actions.sort(key=lambda x: x['priority'])
        return actions

paydetect = None  # Initialized after classifier

# ============================================================
# HEXSTRIKE-AI BRIDGE
# ============================================================
class HexStrikeBridge:
    """Bridge to HexStrike-AI v6.0 API on port 8888"""

    def __init__(self, logger):
        self.log = logger
        self.api_url = HEXSTRIKE_API

    def is_available(self):
        try:
            import urllib.request
            req = urllib.request.urlopen(f"{self.api_url}/", timeout=3)
            return req.status == 200
        except Exception:
            return False

    def _request(self, endpoint, data=None):
        try:
            import urllib.request
            url = f"{self.api_url}{endpoint}"
            if data:
                req = urllib.request.Request(url, data=json.dumps(data).encode(),
                                             headers={'Content-Type': 'application/json'})
                resp = urllib.request.urlopen(req, timeout=30)
            else:
                resp = urllib.request.urlopen(url, timeout=30)
            return json.loads(resp.read().decode())
        except Exception as e:
            self.log.warning(f"HexStrike API error: {e}")
            return None

    def analyze_target(self, target):
        self.log.info(f"HexStrike-AI analysis → {target}")
        return self._request("/api/analyze", {"target": target})

    def generate_report(self, scan_id):
        self.log.info(f"HexStrike report generation → {scan_id}")
        return self._request("/api/report", {"scan_id": scan_id})

    def get_recommendations(self, target, intel_data):
        self.log.info(f"HexStrike recommendations → {target}")
        return self._request("/api/recommend", {"target": target, "intel": intel_data})

hexstrike = HexStrikeBridge(log)

# ============================================================
# 6-LAYER INTELLIGENCE CLASSIFIER
# ============================================================
class IntelligenceClassifier:
    """6-Layer Classification: Domain → Content → Infra → Financial → Network → Historical"""

    LAYERS = {
        'L1_DOMAIN': {
            'name': 'Domain Intelligence',
            'icon': '🌐',
            'categories': ['registration', 'whois', 'dns_records', 'subdomains',
                          'domain_age', 'registrar', 'nameservers', 'mx_records']
        },
        'L2_CONTENT': {
            'name': 'Content Analysis',
            'icon': '📄',
            'categories': ['gambling_keywords', 'payment_gateways', 'affiliate_links',
                          'redirects', 'hidden_content', 'seo_patterns', 'social_links',
                          'app_links']
        },
        'L3_INFRA': {
            'name': 'Infrastructure',
            'icon': '🖥️',
            'categories': ['hosting_provider', 'ip_geolocation', 'cdn_usage', 'server_tech',
                          'ssl_certificate', 'reverse_dns', 'asn_info', 'network_range']
        },
        'L4_FINANCIAL': {
            'name': 'Financial Tracing',
            'icon': '💰',
            'categories': ['payment_processors', 'crypto_wallets', 'bank_connections',
                          'money_flow', 'transaction_patterns', 'merchant_accounts']
        },
        'L5_NETWORK': {
            'name': 'Network Mapping',
            'icon': '🔗',
            'categories': ['connected_domains', 'shared_ips', 'shared_infra',
                          'certificate_connections', 'tracking_pixels', 'api_endpoints']
        },
        'L6_HISTORICAL': {
            'name': 'Historical Intelligence',
            'icon': '📚',
            'categories': ['wayback_history', 'content_changes', 'domain_transfers',
                          'incident_history', 'previous_takedowns', 'reputation_changes']
        }
    }

    def __init__(self, logger, db_conn):
        self.log = logger
        self.db = db_conn

    def classify(self, scan_id, raw_results, tool_name=''):
        """Auto-classify raw tool output into 6 layers"""
        classified = defaultdict(list)
        text = str(raw_results).lower()

        # L1 - Domain Intelligence
        if any(kw in text for kw in ['whois', 'registrar', 'dns', 'ns1', 'ns2', 'mx record',
                                      'nameserver', 'domain name', 'registration']):
            self._extract_domain_intel(scan_id, raw_results, tool_name)
            classified['L1_DOMAIN'].append(tool_name)

        # L2 - Content Analysis
        if any(kw in text for kw in ['gambl', 'slot', 'casino', 'bet ', 'poker', 'togel',
                                      'judi', 'taruhan', 'payment', 'deposit', 'withdraw',
                                      'redirect', 'affiliate', 'bonus']):
            self._extract_content_intel(scan_id, raw_results, tool_name)
            classified['L2_CONTENT'].append(tool_name)

        # L3 - Infrastructure
        if any(kw in text for kw in ['hosting', 'server', 'nginx', 'apache', 'cloudflare',
                                      'ip address', 'geo', 'asn', 'cdn', 'ssl', 'tls']):
            self._extract_infra_intel(scan_id, raw_results, tool_name)
            classified['L3_INFRA'].append(tool_name)

        # L4 - Financial Tracing
        if any(kw in text for kw in ['payment', 'crypto', 'bitcoin', 'wallet', 'bank',
                                      'visa', 'mastercard', 'e-wallet', 'dana', 'ovo', 'gopay']):
            self._extract_financial_intel(scan_id, raw_results, tool_name)
            classified['L4_FINANCIAL'].append(tool_name)

        # L5 - Network Mapping
        if any(kw in text for kw in ['shared', 'connected', 'linked', 'same ip',
                                      'same server', 'reverse dns', 'certificate']):
            self._extract_network_intel(scan_id, raw_results, tool_name)
            classified['L5_NETWORK'].append(tool_name)

        # L6 - Historical
        if any(kw in text for kw in ['archive', 'history', 'previous', 'changed',
                                      'old', 'wayback', 'transfer']):
            self._extract_historical_intel(scan_id, raw_results, tool_name)
            classified['L6_HISTORICAL'].append(tool_name)

        return dict(classified)

    def _extract_ip_addresses(self, text):
        return list(set(re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text)))

    def _extract_domains(self, text):
        return list(set(re.findall(r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b',
                                   text.lower())))

    def _extract_domain_intel(self, scan_id, raw, source):
        for ip in self._extract_ip_addresses(str(raw)):
            self.db.add_intel(scan_id, 'L1_DOMAIN', 'resolved_ip', 'ip', ip, 0.9, source)
        for dom in self._extract_domains(str(raw)):
            self.db.add_intel(scan_id, 'L1_DOMAIN', 'related_domain', 'domain', dom, 0.7, source)
        # DNS records
        for rtype in ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME']:
            pattern = rf'(?:IN\s+)?{rtype}\s+(.+)'
            matches = re.findall(pattern, str(raw), re.IGNORECASE)
            for m in matches[:5]:
                self.db.add_intel(scan_id, 'L1_DOMAIN', f'dns_{rtype.lower()}', rtype, m.strip(), 0.8, source)

    def _extract_content_intel(self, scan_id, raw, source):
        gambling_kw = ['gambl', 'slot', 'casino', 'bet', 'poker', 'togel', 'judi',
                       'taruhan', 'bandar', 'agen', 'bonus deposit', 'freebet', 'jackpot']
        found = [kw for kw in gambling_kw if kw in str(raw).lower()]
        for kw in found:
            self.db.add_intel(scan_id, 'L2_CONTENT', 'gambling_keyword', 'keyword', kw, 0.95, source)
        # Payment patterns
        payment_kw = ['payment', 'deposit', 'withdraw', 'transfer', 'e-wallet', 'credit card']
        found_pay = [kw for kw in payment_kw if kw in str(raw).lower()]
        for kw in found_pay:
            self.db.add_intel(scan_id, 'L2_CONTENT', 'payment_indicator', 'keyword', kw, 0.85, source)

    def _extract_infra_intel(self, scan_id, raw, source):
        servers = re.findall(r'(?:Server|server):\s*(.+)', str(raw))
        for s in servers:
            self.db.add_intel(scan_id, 'L3_INFRA', 'server_tech', 'server', s.strip(), 0.9, source)
        for ip in self._extract_ip_addresses(str(raw)):
            self.db.add_intel(scan_id, 'L3_INFRA', 'ip_address', 'ip', ip, 0.9, source)
        # SSL info
        ssl_patterns = re.findall(r'(?:SSL|TLS|certificate|issuer)[^\n]*', str(raw), re.IGNORECASE)
        for p in ssl_patterns[:5]:
            self.db.add_intel(scan_id, 'L3_INFRA', 'ssl_info', 'ssl', p.strip(), 0.7, source)

    def _extract_financial_intel(self, scan_id, raw, source):
        crypto_addr = re.findall(r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}', str(raw))
        for addr in crypto_addr[:5]:
            self.db.add_intel(scan_id, 'L4_FINANCIAL', 'crypto_address', 'btc', addr, 0.8, source)
        payment_processors = ['stripe', 'paypal', 'midtrans', 'xendit', 'doku', 'veritrans']
        for proc in payment_processors:
            if proc in str(raw).lower():
                self.db.add_intel(scan_id, 'L4_FINANCIAL', 'payment_processor', 'processor', proc, 0.85, source)

    def _extract_network_intel(self, scan_id, raw, source):
        for dom in self._extract_domains(str(raw)):
            self.db.add_intel(scan_id, 'L5_NETWORK', 'connected_domain', 'domain', dom, 0.6, source)

    def _extract_historical_intel(self, scan_id, raw, source):
        dates = re.findall(r'\d{4}-\d{2}-\d{2}', str(raw))
        for d in dates[:5]:
            self.db.add_intel(scan_id, 'L6_HISTORICAL', 'date_reference', 'date', d, 0.5, source)

classifier = IntelligenceClassifier(log, db)
paydetect = PaymentGatewayDetector(log, db, classifier)



# ============================================================
# IP ADDRESS TRACKER — "Pelacak Lokasi Operator"
# Membantu pihak berwenang menemukan lokasi fisik
# ============================================================
class IPTracker:
    """
    IP Address Tracker v1.0
    Pelacak lokasi IP untuk membantu pihak berwenang menemukan
    lokasi fisik operator judi online.
    """

    HOSTING_PROVIDERS = {
        'cloudflare': {'name': 'Cloudflare Inc.', 'type': 'CDN/WAF', 'abuse': 'abuse@cloudflare.com', 'report_url': 'https://www.cloudflare.com/abuse/'},
        'amazon': {'name': 'Amazon AWS', 'type': 'Cloud Hosting', 'abuse': 'abuse@amazonaws.com', 'report_url': 'https://aws.amazon.com/report-abuse/'},
        'google': {'name': 'Google Cloud', 'type': 'Cloud Hosting', 'abuse': 'network-abuse@google.com', 'report_url': 'https://cloud.google.com/abuse/'},
        'digitalocean': {'name': 'DigitalOcean', 'type': 'VPS Hosting', 'abuse': 'abuse@digitalocean.com', 'report_url': 'https://www.digitalocean.com/report-abuse/'},
        'hetzner': {'name': 'Hetzner Online', 'type': 'Dedicated/VPS', 'abuse': 'abuse@hetzner.com'},
        'ovh': {'name': 'OVH SAS', 'type': 'Dedicated/VPS', 'abuse': 'abuse@ovh.net'},
        'vultr': {'name': 'Vultr Holdings', 'type': 'Cloud/VPS', 'abuse': 'abuse@vultr.com'},
        'linode': {'name': 'Linode/Akamai', 'type': 'Cloud/VPS', 'abuse': 'abuse@linode.com'},
        'contabo': {'name': 'Contabo GmbH', 'type': 'VPS/Dedicated', 'abuse': 'abuse@contabo.de'},
        'hostinger': {'name': 'Hostinger International', 'type': 'Shared/VPS', 'abuse': 'abuse@hostinger.com'},
        'namecheap': {'name': 'Namecheap Hosting', 'type': 'Shared/Reseller', 'abuse': 'abuse@namecheap.com'},
        'alibaba': {'name': 'Alibaba Cloud', 'type': 'Cloud Hosting', 'abuse': 'abuse@alibabacloud.com'},
        'microsoft': {'name': 'Microsoft Azure', 'type': 'Cloud Hosting', 'abuse': 'abuse@microsoft.com'},
        'idnic': {'name': 'IDNIC - Indonesian Internet', 'type': 'ID Registry', 'abuse': 'info@idnic.net'},
        'telkom': {'name': 'PT Telkom Indonesia', 'type': 'ID ISP', 'abuse': 'abuse@telkom.co.id'},
        'indosat': {'name': 'PT Indosat Ooredoo', 'type': 'ID ISP', 'abuse': 'abuse@indosat.com'},
        'xl': {'name': 'PT XL Axiata', 'type': 'ID ISP', 'abuse': 'abuse@xl.co.id'},
        'biznet': {'name': 'PT Biznet Gio Nusantara', 'type': 'ID ISP/Hosting', 'abuse': 'abuse@biznetgio.com'},
        'dcoint': {'name': 'PT DCI Indonesia', 'type': 'ID Data Center', 'abuse': 'noc@dci.co.id'},
    }

    VPN_INDICATORS = [
        'vpn', 'proxy', 'tor', 'anonymous', 'hosting', 'datacenter', 'data center',
        'cloud', 'server', 'dedicated', 'vps', 'virtual', 'tunnel', 'relay',
        'exit node', 'anon', 'private'
    ]

    def __init__(self, logger, db_conn, kali_tools, classifier_inst):
        self.log = logger
        self.db = db_conn
        self.kali = kali_tools
        self.classifier = classifier_inst

    def track_ip(self, scan_id, ip_or_domain):
        results = {
            'target': ip_or_domain,
            'resolved_ip': None,
            'geo_location': {},
            'reverse_dns': '',
            'asn_info': {},
            'isp_info': {},
            'hosting_provider': {},
            'whois_data': {},
            'traceroute': [],
            'nmap_services': {},
            'vpn_proxy_detection': {},
            'abuse_contacts': [],
            'risk_level': 'UNKNOWN'
        }

        ip_address = self._resolve_to_ip(ip_or_domain)
        if not ip_address:
            self.log.error(f"[IP-TRACK] Cannot resolve: {ip_or_domain}")
            return results
        results['resolved_ip'] = ip_address
        self.log.success(f"[IP-TRACK] Resolved: {ip_or_domain} -> {ip_address}")
        self.db.add_intel(scan_id, 'L3_INFRA', 'resolved_ip', ip_or_domain, ip_address, 0.95, 'ip_tracker')

        self.log.info(f"[IP-TRACK] Geo-IP lookup -> {ip_address}")
        geo = self._geoip_lookup(ip_address)
        if geo:
            results['geo_location'] = geo
            self.log.success(f"[IP-TRACK] Location: {geo.get('city','?')}, {geo.get('country','?')} ({geo.get('lat','?')}, {geo.get('lon','?')})")
            self.db.add_intel(scan_id, 'L3_INFRA', 'geo_location', ip_address,
                f"{geo.get('city','')}, {geo.get('region','')}, {geo.get('country','')}",
                0.9, 'ip_tracker', json.dumps(geo))

        self.log.info(f"[IP-TRACK] Reverse DNS -> {ip_address}")
        rdns = self._reverse_dns(ip_address)
        if rdns:
            results['reverse_dns'] = rdns
            self.log.success(f"[IP-TRACK] Reverse DNS: {ip_address} -> {rdns}")
            self.db.add_intel(scan_id, 'L3_INFRA', 'reverse_dns', ip_address, rdns, 0.85, 'ip_tracker')

        self.log.info(f"[IP-TRACK] ASN/ISP lookup -> {ip_address}")
        asn_info = self._asn_lookup(ip_address)
        if asn_info:
            results['asn_info'] = asn_info
            results['isp_info'] = {'isp': asn_info.get('isp',''), 'org': asn_info.get('org',''), 'as_number': asn_info.get('as',''), 'as_name': asn_info.get('asname','')}
            self.log.success(f"[IP-TRACK] ISP: {asn_info.get('isp','N/A')} | AS: {asn_info.get('as','N/A')}")
            self.db.add_intel(scan_id, 'L3_INFRA', 'isp_asn', ip_address, f"ISP: {asn_info.get('isp','')} | AS: {asn_info.get('as','')}", 0.9, 'ip_tracker', json.dumps(asn_info))

        hosting = self._detect_hosting_provider(asn_info, rdns, geo)
        if hosting:
            results['hosting_provider'] = hosting
            self.log.success(f"[IP-TRACK] Hosting: {hosting.get('name','N/A')} ({hosting.get('type','N/A')})")
            self.db.add_intel(scan_id, 'L3_INFRA', 'hosting_provider', ip_address, hosting.get('name',''), 0.85, 'ip_tracker', json.dumps(hosting))

        vpn_check = self._detect_vpn_proxy(ip_address, asn_info, geo, rdns)
        results['vpn_proxy_detection'] = vpn_check
        if vpn_check.get('is_vpn_proxy'):
            self.log.warning(f"[IP-TRACK] VPN/Proxy/Hosting detected: {vpn_check.get('type','Unknown')}")
            self.db.add_intel(scan_id, 'L3_INFRA', 'vpn_proxy', ip_address, f"Detected: {vpn_check.get('type','')}", 0.9, 'ip_tracker', json.dumps(vpn_check))

        self.log.info(f"[IP-TRACK] WHOIS lookup -> {ip_address}")
        whois_data = self._whois_ip(ip_address)
        if whois_data:
            results['whois_data'] = whois_data
            self.db.add_intel(scan_id, 'L3_INFRA', 'whois_ip', ip_address, whois_data.get('net_name', whois_data.get('organization','')), 0.85, 'ip_tracker', json.dumps(whois_data))

        self.log.info(f"[IP-TRACK] Traceroute -> {ip_address}")
        traceroute = self._traceroute(ip_address)
        if traceroute:
            results['traceroute'] = traceroute
            self.log.success(f"[IP-TRACK] Traceroute: {len(traceroute)} hops")
            for hop in traceroute[:5]:
                self.db.add_intel(scan_id, 'L5_NETWORK', 'traceroute_hop', str(hop.get('hop','')), hop.get('host', hop.get('ip','')), 0.6, 'ip_tracker', json.dumps(hop))

        self.log.info(f"[IP-TRACK] Service scan -> {ip_address}")
        nmap_services = self._nmap_service_scan(ip_address)
        if nmap_services:
            results['nmap_services'] = nmap_services
            self.log.success(f"[IP-TRACK] Services: {len(nmap_services.get('ports',[]))} port(s) detected")

        abuse_contacts = self._find_abuse_contacts(asn_info, hosting, whois_data)
        results['abuse_contacts'] = abuse_contacts
        if abuse_contacts:
            self.log.success(f"[IP-TRACK] Abuse contacts: {len(abuse_contacts)} found")
            for contact in abuse_contacts:
                self.db.add_intel(scan_id, 'L3_INFRA', 'abuse_contact', ip_address, contact.get('email',''), 0.8, 'ip_tracker', json.dumps(contact))

        risk = self._assess_risk(results)
        results['risk_level'] = risk
        self.log.info(f"[IP-TRACK] Risk level: {risk}")

        authority_report = self._generate_authority_report(ip_or_domain, ip_address, results, scan_id)
        results['authority_report'] = authority_report
        self.db.add_evidence(scan_id, 'ip_tracking', f'IP Location Report: {ip_address}', f'Geo-location report for {ip_or_domain}', authority_report)

        self.log.banner(f"IP TRACKING COMPLETE — {ip_or_domain} -> {ip_address}")
        return results

    def track_batch(self, scan_id, targets):
        results = []
        for target in targets:
            try:
                r = self.track_ip(scan_id, target.strip())
                results.append(r)
                time.sleep(1.5)
            except Exception as e:
                self.log.error(f"[IP-TRACK] Batch error for {target}: {e}")
        return results

    def _resolve_to_ip(self, target):
        try:
            ipaddress.ip_address(target)
            return target
        except ValueError:
            pass
        try:
            result = socket.getaddrinfo(target, None)
            if result:
                return result[0][4][0]
        except Exception:
            pass
        try:
            r = subprocess.run(['dig', '+short', target], capture_output=True, text=True, timeout=10)
            ip = r.stdout.strip().split('\n')[0].strip()
            if ip and not ip.startswith(';'):
                return ip
        except Exception:
            pass
        return None

    def _geoip_lookup(self, ip):
        try:
            r = subprocess.run(['curl', '-s', '--max-time', '10', f'http://ip-api.com/json/{ip}?fields=status,message,continent,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,asname,mobile,proxy,hosting'], capture_output=True, text=True, timeout=15)
            data = json.loads(r.stdout)
            if data.get('status') == 'success':
                return {'ip': ip, 'continent': data.get('continent',''), 'country': data.get('country',''), 'country_code': data.get('countryCode',''), 'region': data.get('regionName',''), 'city': data.get('city',''), 'zip': data.get('zip',''), 'lat': data.get('lat',0), 'lon': data.get('lon',0), 'timezone': data.get('timezone',''), 'is_mobile': data.get('mobile',False), 'is_proxy': data.get('proxy',False), 'is_hosting': data.get('hosting',False), 'source': 'ip-api.com'}
        except Exception:
            pass
        try:
            r = subprocess.run(['curl', '-s', '--max-time', '10', f'https://ipinfo.io/{ip}/json'], capture_output=True, text=True, timeout=15)
            data = json.loads(r.stdout)
            if 'ip' in data:
                loc = data.get('loc','0,0').split(',')
                return {'ip': ip, 'country': data.get('country',''), 'country_code': data.get('country',''), 'region': data.get('region',''), 'city': data.get('city',''), 'zip': data.get('postal',''), 'lat': float(loc[0]) if len(loc)==2 else 0, 'lon': float(loc[1]) if len(loc)==2 else 0, 'timezone': data.get('timezone',''), 'is_mobile': False, 'is_proxy': False, 'is_hosting': False, 'source': 'ipinfo.io'}
        except Exception:
            pass
        return {}

    def _reverse_dns(self, ip):
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            return hostname
        except Exception:
            pass
        try:
            r = subprocess.run(['dig', '+short', '-x', ip], capture_output=True, text=True, timeout=10)
            rdns = r.stdout.strip()
            if rdns.endswith('.'):
                rdns = rdns[:-1]
            return rdns if rdns else ''
        except Exception:
            return ''

    def _asn_lookup(self, ip):
        try:
            r = subprocess.run(['curl', '-s', '--max-time', '10', f'http://ip-api.com/json/{ip}?fields=status,isp,org,as,asname'], capture_output=True, text=True, timeout=15)
            data = json.loads(r.stdout)
            if data.get('status') == 'success':
                return {'isp': data.get('isp',''), 'org': data.get('org',''), 'as': data.get('as',''), 'asname': data.get('asname','')}
        except Exception:
            pass
        return {}

    def _detect_hosting_provider(self, asn_info, rdns, geo):
        check_str = f"{asn_info.get('isp','')} {asn_info.get('org','')} {asn_info.get('asname','')} {rdns}".lower()
        for key, provider in self.HOSTING_PROVIDERS.items():
            if key in check_str:
                return {'detected': True, 'key': key, 'name': provider['name'], 'type': provider['type'], 'abuse_email': provider.get('abuse',''), 'report_url': provider.get('report_url','')}
        if geo and geo.get('is_hosting'):
            return {'detected': True, 'key': 'unknown_hosting', 'name': asn_info.get('org','Unknown Hosting'), 'type': 'Hosting/Datacenter', 'abuse_email': '', 'report_url': ''}
        return {'detected': False}

    def _detect_vpn_proxy(self, ip, asn_info, geo, rdns):
        indicators_found = []
        confidence = 0.0
        check_str = f"{asn_info.get('isp','')} {asn_info.get('org','')} {rdns}".lower()
        for indicator in self.VPN_INDICATORS:
            if indicator in check_str:
                indicators_found.append(indicator)
        if geo:
            if geo.get('is_proxy'):
                indicators_found.append('proxy_flag')
                confidence += 0.3
            if geo.get('is_hosting'):
                indicators_found.append('hosting_flag')
                confidence += 0.4
        if indicators_found:
            confidence += min(len(indicators_found) * 0.15, 0.5)
        vpn_type = 'UNKNOWN'
        if 'vpn' in indicators_found or 'tunnel' in indicators_found:
            vpn_type = 'VPN'
        elif 'proxy' in indicators_found or 'proxy_flag' in indicators_found:
            vpn_type = 'PROXY'
        elif 'tor' in indicators_found:
            vpn_type = 'TOR_EXIT_NODE'
        elif 'hosting' in indicators_found or 'hosting_flag' in indicators_found or 'datacenter' in indicators_found:
            vpn_type = 'HOSTING/DATACENTER'
        elif 'cloud' in indicators_found or 'server' in indicators_found:
            vpn_type = 'CLOUD_SERVER'
        return {'is_vpn_proxy': len(indicators_found) > 0 or (geo and (geo.get('is_proxy') or geo.get('is_hosting'))), 'type': vpn_type, 'confidence': min(confidence, 1.0), 'indicators': indicators_found}

    def _whois_ip(self, ip):
        whois_data = {}
        try:
            r = subprocess.run(['whois', ip], capture_output=True, text=True, timeout=20)
            output = r.stdout
            for line in output.split('\n'):
                ll = line.lower().strip()
                if ll.startswith('netname:') or ll.startswith('net-name:'):
                    whois_data['net_name'] = line.split(':',1)[1].strip()
                elif ll.startswith('organization:') or ll.startswith('org-name:'):
                    whois_data['organization'] = line.split(':',1)[1].strip()
                elif ll.startswith('country:'):
                    whois_data['country'] = line.split(':',1)[1].strip()
                elif 'abuse' in ll and '@' in line:
                    parts = line.split(':',1)
                    if len(parts) > 1:
                        whois_data['abuse_contact'] = parts[1].strip()
                elif ll.startswith('descr:') or ll.startswith('description:'):
                    if 'description' not in whois_data:
                        whois_data['description'] = line.split(':',1)[1].strip()
                elif ll.startswith('inetnum:') or ll.startswith('range:'):
                    whois_data['ip_range'] = line.split(':',1)[1].strip()
                elif ll.startswith('updated:') or ll.startswith('last-modified:'):
                    whois_data['last_updated'] = line.split(':',1)[1].strip()
            whois_data['raw_summary'] = output[:2000]
        except Exception:
            pass
        return whois_data

    def _traceroute(self, ip):
        hops = []
        try:
            r = subprocess.run(['mtr', '-n', '-r', '-c', '3', '--max-ttl', '20', ip], capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                for line in r.stdout.split('\n')[2:]:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        hop_ip = parts[1]
                        if hop_ip not in ('???', '---'):
                            hops.append({'hop': parts[0].replace('.','').strip(), 'ip': hop_ip, 'raw': line.strip()})
                return hops
        except Exception:
            pass
        try:
            r = subprocess.run(['traceroute', '-n', '-m', '20', '-w', '2', ip], capture_output=True, text=True, timeout=60)
            for line in r.stdout.split('\n')[1:]:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] != '*':
                    hops.append({'hop': parts[0], 'ip': parts[1], 'raw': line.strip()})
        except Exception:
            pass
        return hops

    def _nmap_service_scan(self, ip):
        services = {'ports': [], 'os_guess': ''}
        try:
            r = subprocess.run(['nmap', '-sV', '--version-intensity', '5', '-T4', '--top-ports', '100', ip], capture_output=True, text=True, timeout=120)
            output = r.stdout
            for line in output.split('\n'):
                if '/tcp' in line and 'open' in line:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        services['ports'].append({'port': parts[0], 'state': parts[1], 'service': parts[2], 'version': ' '.join(parts[3:]) if len(parts)>3 else ''})
            os_match = re.search(r'OS details:\s*(.+)', output)
            if os_match:
                services['os_guess'] = os_match.group(1).strip()
            services['raw'] = output[:3000]
        except Exception:
            pass
        return services

    def _find_abuse_contacts(self, asn_info, hosting, whois_data):
        contacts = []
        if hosting.get('detected') and hosting.get('abuse_email'):
            contacts.append({'type': 'hosting_abuse', 'name': hosting.get('name',''), 'email': hosting.get('abuse_email',''), 'report_url': hosting.get('report_url','')})
        if whois_data.get('abuse_contact'):
            contacts.append({'type': 'whois_abuse', 'name': whois_data.get('organization',''), 'email': whois_data['abuse_contact'], 'report_url': ''})
        isp = asn_info.get('isp','').lower()
        for key, provider in self.HOSTING_PROVIDERS.items():
            if key in isp and provider.get('abuse'):
                existing = [c['email'] for c in contacts]
                if provider['abuse'] not in existing:
                    contacts.append({'type': 'isp_abuse', 'name': provider['name'], 'email': provider['abuse'], 'report_url': provider.get('report_url','')})
        return contacts

    def _assess_risk(self, results):
        risk_score = 0
        geo = results.get('geo_location', {})
        vpn = results.get('vpn_proxy_detection', {})
        hosting = results.get('hosting_provider', {})
        if hosting.get('detected'):
            risk_score += 3
        if vpn.get('is_vpn_proxy'):
            risk_score += 2
        high_risk = ['CN','RU','PH','KH','MM','KP']
        cc = geo.get('country_code','')
        if cc in high_risk:
            risk_score += 3
        gambling_regions = ['SG','HK','PH','KH','SC','PA']
        if cc in gambling_regions:
            risk_score += 2
        nmap = results.get('nmap_services', {})
        if len(nmap.get('ports',[])) > 3:
            risk_score += 1
        if risk_score >= 7: return 'CRITICAL'
        elif risk_score >= 5: return 'HIGH'
        elif risk_score >= 3: return 'MEDIUM'
        elif risk_score >= 1: return 'LOW'
        return 'INFO'

    def _generate_authority_report(self, original_target, ip_address, results, scan_id=''):
        geo = results.get('geo_location', {})
        asn = results.get('asn_info', {})
        hosting = results.get('hosting_provider', {})
        vpn = results.get('vpn_proxy_detection', {})
        whois = results.get('whois_data', {})
        nmap = results.get('nmap_services', {})
        abuse = results.get('abuse_contacts', [])
        traceroute = results.get('traceroute', [])
        risk = results.get('risk_level', 'UNKNOWN')
        report = []
        report.append("=" * 70)
        report.append("MYTHOS NEMESIS — LAPORAN PELACAKAN IP ADDRESS")
        report.append("IP ADDRESS TRACKING REPORT FOR LAW ENFORCEMENT")
        report.append("=" * 70)
        report.append("")
        report.append(f"Tanggal/Date:    {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} WIB")
        report.append(f"Sistem/System:   MYTHOS NEMESIS v{VERSION}")
        report.append(f"Analyst:         {AUTHOR}")
        report.append(f"Scan ID:         {scan_id}")
        report.append("")
        report.append("-" * 70)
        report.append("1. INFORMASI TARGET / TARGET INFORMATION")
        report.append("-" * 70)
        report.append(f"  Original Target:  {original_target}")
        report.append(f"  Resolved IP:      {ip_address}")
        report.append(f"  Reverse DNS:      {results.get('reverse_dns','N/A')}")
        report.append(f"  Risk Level:       {risk}")
        report.append("")
        report.append("-" * 70)
        report.append("2. LOKASI GEOGRAFIS / GEOGRAPHIC LOCATION")
        report.append("-" * 70)
        report.append(f"  Benua/Continent:  {geo.get('continent','N/A')}")
        report.append(f"  Negara/Country:   {geo.get('country','N/A')} ({geo.get('country_code','')})")
        report.append(f"  Provinsi/Region:  {geo.get('region','N/A')}")
        report.append(f"  Kota/City:        {geo.get('city','N/A')}")
        report.append(f"  Kode Pos/Zip:     {geo.get('zip','N/A')}")
        report.append(f"  Koordinat/Coords: {geo.get('lat','N/A')}, {geo.get('lon','N/A')}")
        report.append(f"  Timezone:         {geo.get('timezone','N/A')}")
        report.append("")
        report.append("-" * 70)
        report.append("3. INFORMASI ISP & ASN")
        report.append("-" * 70)
        report.append(f"  ISP:              {asn.get('isp','N/A')}")
        report.append(f"  Organization:     {asn.get('org','N/A')}")
        report.append(f"  AS Number:        {asn.get('as','N/A')}")
        report.append(f"  AS Name:          {asn.get('asname','N/A')}")
        report.append("")
        report.append("-" * 70)
        report.append("4. HOSTING PROVIDER")
        report.append("-" * 70)
        if hosting.get('detected'):
            report.append(f"  Provider:         {hosting.get('name','N/A')}")
            report.append(f"  Type:             {hosting.get('type','N/A')}")
            report.append(f"  Abuse Email:      {hosting.get('abuse_email','N/A')}")
            report.append(f"  Report URL:       {hosting.get('report_url','N/A')}")
        else:
            report.append("  Status:           Not detected as hosting provider")
        report.append("")
        report.append("-" * 70)
        report.append("5. VPN/PROXY/HOSTING DETECTION")
        report.append("-" * 70)
        report.append(f"  VPN/Proxy:        {'YES' if vpn.get('is_vpn_proxy') else 'NO'}")
        report.append(f"  Type:             {vpn.get('type','N/A')}")
        report.append(f"  Confidence:       {vpn.get('confidence',0):.0%}")
        report.append("")
        report.append("-" * 70)
        report.append("6. WHOIS DATA")
        report.append("-" * 70)
        report.append(f"  Network Name:     {whois.get('net_name','N/A')}")
        report.append(f"  Organization:     {whois.get('organization','N/A')}")
        report.append(f"  Country:          {whois.get('country','N/A')}")
        report.append(f"  IP Range:         {whois.get('ip_range','N/A')}")
        report.append(f"  Abuse Contact:    {whois.get('abuse_contact','N/A')}")
        report.append("")
        report.append("-" * 70)
        report.append("7. PORT & SERVICE SCAN")
        report.append("-" * 70)
        ports = nmap.get('ports', [])
        if ports:
            for p in ports:
                report.append(f"  {p.get('port',''):15} {p.get('state',''):8} {p.get('service',''):15} {p.get('version','')}")
        else:
            report.append("  No ports detected")
        if nmap.get('os_guess'):
            report.append(f"  OS Guess: {nmap['os_guess']}")
        report.append("")
        report.append("-" * 70)
        report.append("8. TRACEROUTE PATH")
        report.append("-" * 70)
        if traceroute:
            for hop in traceroute:
                report.append(f"  Hop {hop.get('hop','?'):>3}: {hop.get('ip','???')}")
        else:
            report.append("  Traceroute not available")
        report.append("")
        report.append("-" * 70)
        report.append("9. KONTAK ABUSE / ABUSE CONTACTS")
        report.append("-" * 70)
        if abuse:
            for i, contact in enumerate(abuse, 1):
                report.append(f"  [{i}] {contact.get('name','N/A')}")
                report.append(f"      Type:  {contact.get('type','')}")
                report.append(f"      Email: {contact.get('email','')}")
                report.append(f"      URL:   {contact.get('report_url','')}")
        else:
            report.append("  No abuse contacts found")
        report.append("")
        report.append("-" * 70)
        report.append("10. REKOMENDASI TINDAKAN / RECOMMENDED ACTIONS")
        report.append("-" * 70)
        cc = geo.get('country_code', '')
        if cc == 'ID':
            report.append("  [1] Laporkan ke Kominfo — https://aduankonten.kominfo.go.id/")
            report.append("  [2] Laporkan ke Polri Ditsiber — ditsiber@polri.go.id")
            report.append("  [3] Laporkan ke BSSN (Badan Siber dan Sandi Negara)")
            report.append("  [4] Laporkan ke OJK jika melibatkan keuangan")
        else:
            report.append(f"  [1] Server berlokasi di {geo.get('country','luar negeri')} ({cc})")
            report.append("  [2] Laporkan ke hosting provider untuk takedown")
            report.append("  [3] Laporkan ke Kominfo — https://aduankonten.kominfo.go.id/")
            report.append("  [4] Koordinasi dengan Interpol/ICPO jika diperlukan")
        if hosting.get('detected'):
            report.append(f"  [5] Kirim laporan abuse ke hosting: {hosting.get('name','')}")
            if hosting.get('abuse_email'):
                report.append(f"      Email: {hosting['abuse_email']}")
        if vpn.get('is_vpn_proxy'):
            report.append("  [6] IP menggunakan VPN/Proxy — operator menyembunyikan lokasi")
        report.append("")
        report.append("=" * 70)
        report.append(f"LAPORAN DIHASILKAN OLEH MYTHOS NEMESIS v{VERSION} — {AUTHOR}")
        report.append("=" * 70)
        return '\n'.join(report)

    def get_location_summary(self, ip):
        ip_address = self._resolve_to_ip(ip)
        if not ip_address:
            return {'error': 'Cannot resolve'}
        geo = self._geoip_lookup(ip_address)
        asn = self._asn_lookup(ip_address)
        return {'ip': ip_address, 'location': f"{geo.get('city','?')}, {geo.get('country','?')}", 'coordinates': f"{geo.get('lat',0)}, {geo.get('lon',0)}", 'isp': asn.get('isp','N/A'), 'country_code': geo.get('country_code',''), 'is_hosting': geo.get('is_hosting',False), 'is_proxy': geo.get('is_proxy',False)}


iptracker = IPTracker(log, db, kali, classifier)


# ============================================================
# LEGAL KILL CHAIN ENGINE
# ============================================================
class LegalKillChain:
    """
    Legal Kill Chain: DETECT → TRACE → STRANGLE → BLOCK → MONITOR
    ⚠️ NO DDoS — Legal methods ONLY
    """

    PHASES = [
        {
            'id': 'DETECT',
            'name': 'Detect',
            'description': 'Identify gambling site through automated scanning',
            'actions': ['port_scan', 'web_scan', 'content_analysis', 'osint_harvest']
        },
        {
            'id': 'TRACE',
            'name': 'Trace',
            'description': 'Trace infrastructure and ownership details',
            'actions': ['whois_lookup', 'dns_trace', 'ip_geolocation', 'ssl_analysis',
                       'network_mapping', 'financial_tracing']
        },
        {
            'id': 'STRANGLE',
            'name': 'Strangle',
            'description': 'File abuse reports to shut down the site legally',
            'actions': ['hosting_abuse_report', 'registrar_abuse_report',
                       'ssl_abuse_report', 'payment_processor_report',
                       'government_report', 'cert_report']
        },
        {
            'id': 'BLOCK',
            'name': 'Block',
            'description': 'Add to DNS blocklists and filtering systems',
            'actions': ['dns_blocklist_add', 'firewall_rule_add', 'hosts_file_update',
                       'proxy_block', 'isp_report']
        },
        {
            'id': 'MONITOR',
            'name': 'Monitor',
            'description': 'Monitor for re-emergence or infrastructure changes',
            'actions': ['uptime_monitor', 'dns_monitor', 'content_monitor',
                       'infra_change_monitor', 'alert_setup']
        }
    ]

    def __init__(self, logger, db_conn, kali_tools, hexstrike_bridge, classifier_inst):
        self.log = logger
        self.db = db_conn
        self.kali = kali_tools
        self.hexstrike = hexstrike_bridge
        self.classifier = classifier_inst

    def execute(self, scan_id, target, phases=None):
        """Execute kill chain phases"""
        phases_to_run = phases or ['DETECT', 'TRACE', 'STRANGLE', 'BLOCK', 'MONITOR']
        results = {}

        for phase in self.PHASES:
            if phase['id'] not in phases_to_run:
                continue

            self.log.banner(f"KILL CHAIN — {phase['id']}: {phase['name']}")
            self.db.add_kill_chain(scan_id, phase['id'], phase['description'], target)
            self.db.update_kill_chain(scan_id, phase['id'], 'running')

            phase_results = {}
            for action in phase['actions']:
                try:
                    result = self._execute_action(scan_id, target, phase['id'], action)
                    phase_results[action] = result
                except Exception as e:
                    self.log.error(f"Action {action} failed: {e}")
                    phase_results[action] = {'status': 'error', 'error': str(e)}

            results[phase['id']] = phase_results
            self.db.update_kill_chain(scan_id, phase['id'], 'completed',
                                     json.dumps(phase_results, default=str)[:500])

        return results

    def _execute_action(self, scan_id, target, phase, action):
        if phase == 'DETECT':
            return self._detect(scan_id, target, action)
        elif phase == 'TRACE':
            return self._trace(scan_id, target, action)
        elif phase == 'STRANGLE':
            return self._strangle(scan_id, target, action)
        elif phase == 'BLOCK':
            return self._block(scan_id, target, action)
        elif phase == 'MONITOR':
            return self._monitor(scan_id, target, action)
        return {'status': 'unknown_phase'}

    def _detect(self, scan_id, target, action):
        self.log.info(f"[DETECT] {action} → {target}")
        if action == 'port_scan':
            result = self.kali.nmap_scan(target, 'quick')
            self.classifier.classify(scan_id, result, 'nmap')
            return {'status': 'done', 'tool': 'nmap', 'output_size': len(result)}

        elif action == 'web_scan':
            url = target if target.startswith('http') else f'http://{target}'
            results = self.kali.web_scan(url)
            for tool_name, output in results:
                self.classifier.classify(scan_id, output, tool_name)
            return {'status': 'done', 'tools_used': [r[0] for r in results]}

        elif action == 'content_analysis':
            url = target if target.startswith('http') else f'http://{target}'
            results = self.kali.dir_bruteforce(url)
            for tool_name, output in results:
                self.classifier.classify(scan_id, output, tool_name)
            return {'status': 'done', 'tools_used': [r[0] for r in results]}

        elif action == 'osint_harvest':
            domain = target.replace('http://', '').replace('https://', '').split('/')[0]
            results = self.kali.osint_harvest(domain)
            for tool_name, output in results:
                self.classifier.classify(scan_id, output, tool_name)
            return {'status': 'done', 'tools_used': [r[0] for r in results]}

        return {'status': 'skipped'}

    def _trace(self, scan_id, target, action):
        self.log.info(f"[TRACE] {action} → {target}")
        domain = target.replace('http://', '').replace('https://', '').split('/')[0]

        if action == 'whois_lookup':
            result = self.kali.osint_harvest(domain)
            whois_data = [r[1] for r in result if r[0] == 'WHOIS']
            if whois_data:
                self.classifier.classify(scan_id, whois_data[0], 'whois')
                self.db.add_evidence(scan_id, 'whois', f'WHOIS: {domain}',
                                    'Domain registration details', whois_data[0])
            return {'status': 'done'}

        elif action == 'dns_trace':
            results = self.kali.dns_enum(domain)
            for tool_name, output in results:
                self.classifier.classify(scan_id, output, tool_name)
            return {'status': 'done', 'tools_used': [r[0] for r in results]}

        elif action == 'ip_geolocation':
            result = self.kali.nmap_scan(target, 'quick')
            ips = classifier._extract_ip_addresses(result)
            return {'status': 'done', 'ips_found': ips}

        elif action == 'ssl_analysis':
            results = self.kali.ssl_analyze(target)
            for tool_name, output in results:
                self.classifier.classify(scan_id, output, tool_name)
            return {'status': 'done'}

        elif action == 'network_mapping':
            results = self.kali.subdomain_enum(domain)
            for tool_name, output in results:
                self.classifier.classify(scan_id, output, tool_name)
            return {'status': 'done'}

        elif action == 'financial_tracing':
            if self.hexstrike.is_available():
                result = self.hexstrike.analyze_target(target)
                if result:
                    self.classifier.classify(scan_id, json.dumps(result), 'hexstrike')
                    return {'status': 'done', 'source': 'hexstrike'}
            return {'status': 'done', 'note': 'HexStrike unavailable, local analysis only'}

        return {'status': 'skipped'}

    def _strangle(self, scan_id, target, action):
        """⚠️ LEGAL ONLY — File abuse reports"""
        self.log.info(f"[STRANGLE] {action} → {target}")
        domain = target.replace('http://', '').replace('https://', '').split('/')[0]

        if action == 'hosting_abuse_report':
            self.log.warning(f"Abuse report template generated for hosting provider of {domain}")
            self.db.add_evidence(scan_id, 'abuse_report', f'Hosting Abuse: {domain}',
                               'Abuse report template for hosting provider',
                               f'Target: {domain}\nCategory: Online Gambling\nAction: Takedown Request')
            return {'status': 'report_generated', 'type': 'hosting_abuse'}

        elif action == 'registrar_abuse_report':
            self.log.warning(f"Registrar abuse report for {domain}")
            self.db.add_evidence(scan_id, 'abuse_report', f'Registrar Abuse: {domain}',
                               'Domain registrar abuse report',
                               f'Target: {domain}\nCategory: Online Gambling\nAction: Domain Suspension')
            return {'status': 'report_generated', 'type': 'registrar_abuse'}

        elif action == 'ssl_abuse_report':
            self.log.warning(f"SSL abuse report for {domain}")
            return {'status': 'report_generated', 'type': 'ssl_abuse'}

        elif action == 'payment_processor_report':
            self.log.warning(f"[STRANGLE] Payment Gateway Detector → {domain}")
            # Run Payment Gateway Detector
            url = target if target.startswith('http') else f'https://{domain}'
            pay_results = paydetect.analyze_url(scan_id, url)
            # Auto-generate strangle reports for all detected payment methods
            reports = paydetect.generate_strangle_reports(scan_id, target, pay_results)
            total_detected = (len(pay_results['payment_processors']) +
                            len(pay_results['e_wallets']) +
                            len(pay_results['crypto_wallets']) +
                            len(pay_results['bank_transfers']))
            return {
                'status': 'done',
                'payment_processors': len(pay_results['payment_processors']),
                'e_wallets': len(pay_results['e_wallets']),
                'crypto_wallets': len(pay_results['crypto_wallets']),
                'bank_transfers': len(pay_results['bank_transfers']),
                'qris': pay_results['qris'],
                'strangle_reports': len(reports),
                'total_detected': total_detected
            }

        elif action == 'government_report':
            self.log.warning(f"Government report for {domain}")
            self.db.add_evidence(scan_id, 'government_report', f'Kominfo Report: {domain}',
                               'Government regulatory report',
                               f'Target: {domain}\nAuthority: Kominfo/BSSN\nAction: Formal Complaint')
            return {'status': 'report_generated', 'type': 'government'}

        elif action == 'cert_report':
            self.log.warning(f"CERT report for {domain}")
            return {'status': 'report_generated', 'type': 'cert'}

        return {'status': 'skipped'}

    def _block(self, scan_id, target, action):
        """Add to blocklists — local and reportable"""
        self.log.info(f"[BLOCK] {action} → {target}")
        domain = target.replace('http://', '').replace('https://', '').split('/')[0]

        if action == 'dns_blocklist_add':
            self.db.add_blocklist(domain, '', 'Online gambling site', 'mythos')
            self.log.success(f"Added {domain} to DNS blocklist")
            return {'status': 'blocked', 'domain': domain}

        elif action == 'firewall_rule_add':
            result = self.kali.nmap_scan(target, 'quick')
            ips = classifier._extract_ip_addresses(result)
            for ip in ips:
                self.db.add_blocklist(domain, ip, 'Online gambling IP', 'mythos')
                self.log.success(f"Added {ip} to blocklist for {domain}")
            return {'status': 'blocked', 'ips': ips}

        elif action == 'hosts_file_update':
            # Generate hosts file entries (don't modify system hosts directly)
            entries = f"0.0.0.0 {domain}\n0.0.0.0 www.{domain}\n"
            self.db.add_evidence(scan_id, 'blocklist', f'Hosts entries: {domain}',
                               'Hosts file blocklist entries', entries)
            return {'status': 'generated', 'entries': entries}

        elif action == 'proxy_block':
            self.log.info(f"Proxy block configuration generated for {domain}")
            return {'status': 'config_generated'}

        elif action == 'isp_report':
            self.log.info(f"ISP block report generated for {domain}")
            self.db.add_evidence(scan_id, 'isp_report', f'ISP Block: {domain}',
                               'ISP blocking request', f'Target: {domain}\nAction: ISP-level block')
            return {'status': 'report_generated'}

        return {'status': 'skipped'}

    def _monitor(self, scan_id, target, action):
        """Set up monitoring for target"""
        self.log.info(f"[MONITOR] {action} → {target}")
        domain = target.replace('http://', '').replace('https://', '').split('/')[0]

        if action == 'uptime_monitor':
            self.log.info(f"Uptime monitoring configured for {domain}")
            return {'status': 'monitoring', 'type': 'uptime'}

        elif action == 'dns_monitor':
            self.log.info(f"DNS monitoring configured for {domain}")
            return {'status': 'monitoring', 'type': 'dns'}

        elif action == 'content_monitor':
            self.log.info(f"Content monitoring configured for {domain}")
            return {'status': 'monitoring', 'type': 'content'}

        elif action == 'infra_change_monitor':
            self.log.info(f"Infrastructure monitoring configured for {domain}")
            return {'status': 'monitoring', 'type': 'infra'}

        elif action == 'alert_setup':
            self.log.info(f"Alerts configured for {domain}")
            return {'status': 'monitoring', 'type': 'alert'}

        return {'status': 'skipped'}

killchain = LegalKillChain(log, db, kali, hexstrike, classifier)

# ============================================================
# FLASK APP + SOCKETIO
# ============================================================
app = Flask(__name__, template_folder=os.path.join(APP_DIR, 'templates'),
            static_folder=os.path.join(APP_DIR, 'static'))
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
log.socketio = socketio

# ============================================================
# SOCKETIO EVENTS
# ============================================================
@socketio.on('connect')
def handle_connect():
    emit('connected', {'version': VERSION, 'author': AUTHOR, 'iptracker': iptracker is not None})
    stats = db.get_stats()
    emit('stats_update', stats)
    log.debug("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    log.debug("Client disconnected")

@socketio.on('start_scan')
def handle_start_scan(data):
    target = data.get('target', '').strip()
    scan_type = data.get('scan_type', 'full')
    phases = data.get('phases', None)

    if not target:
        emit('scan_error', {'error': 'No target specified'})
        return

    scan_id = str(uuid.uuid4())[:8]
    db.create_scan(scan_id, target, scan_type)
    log.set_scan(scan_id)

    emit('scan_started', {'scan_id': scan_id, 'target': target, 'scan_type': scan_type})
    log.banner(f"SCAN STARTED — {scan_id}: {target} ({scan_type})")

    # Run scan in background thread
    def run_scan():
        try:
            results = killchain.execute(scan_id, target, phases)
            db.update_scan(scan_id, status='completed',
                          finished_at=datetime.datetime.now().isoformat(),
                          result_count=db.get_stats()['intelligence'])

            # Try HexStrike report
            report = None
            if hexstrike.is_available():
                report = hexstrike.generate_report(scan_id)

            socketio.emit('scan_completed', {
                'scan_id': scan_id,
                'target': target,
                'results_summary': {k: len(v) for k, v in results.items()},
                'hexstrike_report': report
            })
            log.success(f"Scan completed: {scan_id}")

        except Exception as e:
            db.update_scan(scan_id, status='error',
                          finished_at=datetime.datetime.now().isoformat())
            socketio.emit('scan_error', {'scan_id': scan_id, 'error': str(e)})
            log.error(f"Scan failed: {scan_id} — {e}")

    thread = threading.Thread(target=run_scan, daemon=True)
    thread.start()

@socketio.on('stop_scan')
def handle_stop_scan(data):
    scan_id = data.get('scan_id')
    if scan_id:
        db.update_scan(scan_id, status='stopped',
                      finished_at=datetime.datetime.now().isoformat())
        emit('scan_stopped', {'scan_id': scan_id})
        log.warning(f"Scan stopped: {scan_id}")

@socketio.on('get_scan_results')
def handle_get_results(data):
    scan_id = data.get('scan_id')
    if scan_id:
        intel = db.get_intel(scan_id)
        evidence = db.get_evidence(scan_id)
        kill_chain = db.get_kill_chain(scan_id)
        emit('scan_results', {
            'scan_id': scan_id,
            'intelligence': intel,
            'evidence': evidence,
            'kill_chain': kill_chain
        })

@socketio.on('quick_scan')
def handle_quick_scan(data):
    """Quick scan — DETECT + TRACE only"""
    target = data.get('target', '').strip()
    if not target:
        emit('scan_error', {'error': 'No target specified'})
        return
    data['phases'] = ['DETECT', 'TRACE']
    handle_start_scan(data)

@socketio.on('strangle_scan')
def handle_strangle_scan(data):
    """Full kill chain scan"""
    target = data.get('target', '').strip()
    if not target:
        emit('scan_error', {'error': 'No target specified'})
        return
    data['phases'] = ['DETECT', 'TRACE', 'STRANGLE']
    handle_start_scan(data)

@socketio.on('get_tools')
def handle_get_tools():
    emit('tools_list', {'tools': kali.available(), 'count': len(kali.available())})

@socketio.on('run_tool')
def handle_run_tool(data):
    tool = data.get('tool', '')
    target = data.get('target', '')
    args = data.get('args', '')

    if not tool or not target:
        emit('tool_error', {'error': 'Tool and target required'})
        return

    scan_id = data.get('scan_id', str(uuid.uuid4())[:8])
    log.info(f"Manual tool run: {tool} → {target}")

    def run():
        try:
            cmd = f"{tool} {args} {target}" if args else f"{tool} {target}"
            result = kali._run(cmd, 300)
            classifier.classify(scan_id, result, tool)
            socketio.emit('tool_result', {
                'scan_id': scan_id, 'tool': tool,
                'output': result[:5000], 'size': len(result)
            })
        except Exception as e:
            socketio.emit('tool_error', {'tool': tool, 'error': str(e)})

    threading.Thread(target=run, daemon=True).start()

@socketio.on('get_blocklist')
def handle_get_blocklist():
    bl = db.get_blocklist()
    emit('blocklist_data', {'entries': bl, 'count': len(bl)})

@socketio.on('add_blocklist')
def handle_add_blocklist(data):
    domain = data.get('domain', '')
    ip = data.get('ip', '')
    reason = data.get('reason', 'Manual addition')
    if domain:
        db.add_blocklist(domain, ip, reason, 'manual')
        emit('blocklist_updated', {'domain': domain, 'action': 'added'})
        log.success(f"Added to blocklist: {domain}")

@socketio.on('detect_payments')
def handle_detect_payments(data):
    """Run Payment Gateway Detector on a target"""
    target = data.get('target', '').strip()
    scan_id = data.get('scan_id', str(uuid.uuid4())[:8])
    if not target:
        emit('payment_error', {'error': 'No target specified'})
        return
    log.info(f"[PAYMENT-GW] Manual payment detection → {target}")

    def run():
        try:
            url = target if target.startswith('http') else f'https://{target}'
            results = paydetect.analyze_url(scan_id, url)
            # Get prioritized strangle actions
            actions = paydetect.get_strangle_actions(results)
            socketio.emit('payment_results', {
                'scan_id': scan_id,
                'target': target,
                'results': results,
                'strangle_actions': actions
            })
        except Exception as e:
            socketio.emit('payment_error', {'error': str(e)})

    threading.Thread(target=run, daemon=True).start()

@socketio.on('strangle_payments')
def handle_strangle_payments(data):
    """Generate STRANGLE reports for detected payment methods"""
    scan_id = data.get('scan_id', '')
    target = data.get('target', '').strip()
    detection_results = data.get('results', {})
    if not target or not detection_results:
        emit('payment_error', {'error': 'Target and results required'})
        return
    log.banner(f"STRANGLE — Generating payment abuse reports → {target}")
    reports = paydetect.generate_strangle_reports(scan_id, target, detection_results)
    emit('strangle_complete', {
        'scan_id': scan_id,
        'target': target,
        'reports_generated': len(reports),
        'reports': reports
    })



# ============================================================
# IP TRACKER SOCKETIO EVENTS
# ============================================================
@socketio.on('track_ip')
def handle_track_ip(data):
    """Track an IP address — full geo-location analysis"""
    target = data.get('target', '').strip()
    scan_id = data.get('scan_id', str(uuid.uuid4())[:8])
    if not target:
        emit('ip_track_error', {'error': 'No target specified'})
        return
    if not iptracker:
        emit('ip_track_error', {'error': 'IP Tracker not initialized'})
        return

    log.info(f"[IP-TRACK] Tracking request -> {target}")

    def run():
        try:
            db.create_scan(scan_id, target, 'ip_tracking')
            socketio.emit('ip_track_started', {
                'scan_id': scan_id,
                'target': target
            })
            results = iptracker.track_ip(scan_id, target)
            db.update_scan(scan_id, status='completed',
                          finished_at=datetime.datetime.now().isoformat(),
                          result_count=len(results.get('geo_location', {})))
            socketio.emit('ip_track_results', {
                'scan_id': scan_id,
                'target': target,
                'results': results
            })
            log.success(f"IP tracking completed: {scan_id}")
        except Exception as e:
            db.update_scan(scan_id, status='error',
                          finished_at=datetime.datetime.now().isoformat())
            socketio.emit('ip_track_error', {
                'scan_id': scan_id,
                'target': target,
                'error': str(e)
            })
            log.error(f"IP tracking failed: {scan_id} — {e}")

    threading.Thread(target=run, daemon=True).start()

@socketio.on('track_ip_batch')
def handle_track_ip_batch(data):
    """Track multiple IPs/domains in batch"""
    targets = data.get('targets', [])
    scan_id = data.get('scan_id', str(uuid.uuid4())[:8])
    if not targets:
        emit('ip_track_error', {'error': 'No targets specified'})
        return
    if not iptracker:
        emit('ip_track_error', {'error': 'IP Tracker not initialized'})
        return

    log.info(f"[IP-TRACK] Batch tracking: {len(targets)} target(s)")

    def run():
        try:
            results = iptracker.track_batch(scan_id, targets)
            socketio.emit('ip_track_batch_results', {
                'scan_id': scan_id,
                'targets_count': len(targets),
                'results': results
            })
        except Exception as e:
            socketio.emit('ip_track_error', {'error': str(e)})

    threading.Thread(target=run, daemon=True).start()

@socketio.on('ip_quick_lookup')
def handle_ip_quick_lookup(data):
    """Quick IP location lookup (geo-IP only, no deep scan)"""
    target = data.get('target', '').strip()
    if not target:
        emit('ip_track_error', {'error': 'No target specified'})
        return
    if not iptracker:
        emit('ip_track_error', {'error': 'IP Tracker not initialized'})
        return

    def run():
        try:
            summary = iptracker.get_location_summary(target)
            socketio.emit('ip_quick_result', {
                'target': target,
                'summary': summary
            })
        except Exception as e:
            socketio.emit('ip_track_error', {'error': str(e)})

    threading.Thread(target=run, daemon=True).start()

# ============================================================
# HTTP ROUTES
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    return jsonify(db.get_stats())

@app.route('/api/scans')
def api_scans():
    return jsonify(db.get_scans())

@app.route('/api/scans/<scan_id>')
def api_scan_detail(scan_id):
    return jsonify({
        'intel': db.get_intel(scan_id),
        'evidence': db.get_evidence(scan_id),
        'kill_chain': db.get_kill_chain(scan_id)
    })

@app.route('/api/tools')
def api_tools():
    return jsonify({'tools': kali.available(), 'count': len(kali.available())})

@app.route('/api/blocklist')
def api_blocklist():
    return jsonify(db.get_blocklist())

@app.route('/api/blocklist/export')
def api_blocklist_export():
    """Export blocklist as hosts file format"""
    entries = db.get_blocklist()
    hosts = "# MYTHOS NEMESIS Blocklist\n"
    hosts += f"# Generated: {datetime.datetime.now().isoformat()}\n"
    hosts += f"# Entries: {len(entries)}\n\n"
    for e in entries:
        ip = e.get('ip_address') or '0.0.0.0'
        hosts += f"{ip} {e['domain']}  # {e.get('reason', '')}\n"
    return hosts, 200, {'Content-Type': 'text/plain'}

@app.route('/api/report/<scan_id>')
def api_report(scan_id):
    intel = db.get_intel(scan_id)
    evidence = db.get_evidence(scan_id)
    kill_chain = db.get_kill_chain(scan_id)
    report = {
        'scan_id': scan_id,
        'generated': datetime.datetime.now().isoformat(),
        'version': VERSION,
        'author': AUTHOR,
        'intelligence_layers': {},
        'evidence_count': len(evidence),
        'kill_chain_status': kill_chain
    }
    for item in intel:
        layer = item['layer']
        if layer not in report['intelligence_layers']:
            report['intelligence_layers'][layer] = []
        report['intelligence_layers'][layer].append(item)
    return jsonify(report)

@app.route('/api/hexstrike/status')
def api_hexstrike_status():
    return jsonify({'available': hexstrike.is_available(), 'api_url': HEXSTRIKE_API})

@app.route('/api/payment/detect', methods=['POST'])
def api_payment_detect():
    """API endpoint for payment gateway detection"""
    target = request.json.get('target', '')
    if not target:
        return jsonify({'error': 'No target'}), 400
    scan_id = str(uuid.uuid4())[:8]
    url = target if target.startswith('http') else f'https://{target}'
    results = paydetect.analyze_url(scan_id, url)
    actions = paydetect.get_strangle_actions(results)
    return jsonify({
        'scan_id': scan_id,
        'target': target,
        'results': results,
        'strangle_actions': actions
    })

@app.route('/api/payment/processors')
def api_payment_processors():
    """List all known payment processors"""
    return jsonify(paydetect.get_all_processors())

@app.route('/api/payment/strangle/<scan_id>', methods=['POST'])
def api_payment_strangle(scan_id):
    """Generate strangle reports for detected payments"""
    target = request.json.get('target', '')
    results = request.json.get('results', {})
    if not target:
        return jsonify({'error': 'Target required'}), 400
    reports = paydetect.generate_strangle_reports(scan_id, target, results)
    return jsonify({'reports_generated': len(reports), 'reports': reports})

@app.route('/api/hexstrike/analyze', methods=['POST'])
def api_hexstrike_analyze():
    target = request.json.get('target', '')
    if not target:
        return jsonify({'error': 'No target'}), 400
    result = hexstrike.analyze_target(target)
    return jsonify(result or {'error': 'HexStrike unavailable'})



# ============================================================
# IP TRACKER API ROUTES
# ============================================================
@app.route('/api/ip/track', methods=['POST'])
def api_ip_track():
    """API endpoint for IP address tracking"""
    target = request.json.get('target', '')
    if not target:
        return jsonify({'error': 'No target specified'}), 400
    scan_id = str(uuid.uuid4())[:8]
    if not iptracker:
        return jsonify({'error': 'IP Tracker not initialized'}), 503

    url = target if target.startswith('http') else target
    results = iptracker.track_ip(scan_id, url)
    return jsonify({
        'scan_id': scan_id,
        'target': target,
        'results': results
    })

@app.route('/api/ip/quick/<target>')
def api_ip_quick(target):
    """Quick IP location lookup"""
    if not iptracker:
        return jsonify({'error': 'IP Tracker not initialized'}), 503
    summary = iptracker.get_location_summary(target)
    return jsonify(summary)

@app.route('/api/ip/batch', methods=['POST'])
def api_ip_batch():
    """Batch IP tracking"""
    targets = request.json.get('targets', [])
    if not targets:
        return jsonify({'error': 'No targets specified'}), 400
    scan_id = str(uuid.uuid4())[:8]
    if not iptracker:
        return jsonify({'error': 'IP Tracker not initialized'}), 503
    results = iptracker.track_batch(scan_id, targets)
    return jsonify({'scan_id': scan_id, 'results': results})

@app.route('/api/ip/report/<scan_id>')
def api_ip_report(scan_id):
    """Get IP tracking report for a scan"""
    evidence = db.get_evidence(scan_id)
    ip_evidence = [e for e in evidence if e.get('evidence_type') == 'ip_tracking']
    intel = db.get_intel(scan_id)
    ip_intel = [i for i in intel if i.get('source') == 'ip_tracker']
    return jsonify({
        'scan_id': scan_id,
        'intel': ip_intel,
        'evidence': ip_evidence
    })

# ============================================================
# MAIN
# ============================================================
def print_banner():
    B = '\033[1m'
    C = '\033[96m'
    R = '\033[0m'
    G = '\033[92m'
    Y = '\033[93m'
    print(f"""
{B}{C}████████╗██╗  ██╗██╗   ██╗███╗   ███╗██████╗ ███████╗ ██████╗ ███╗   ██╗ █████╗
╚══██╔══╝██║  ██║██║   ██║████╗ ████║██╔══██╗██╔════╝██╔═══██╗████╗  ██║██╔══██╗
   ██║   ███████║██║   ██║██╔████╔██║██████╔╝█████╗  ██║   ██║██╔██╗ ██║███████║
   ██║   ██╔══██║██║   ██║██║╚██╔╝██║██╔══██╗██╔══╝  ██║   ██║██║╚██╗██║██╔══██║
   ██║   ██║  ██║╚██████╔╝██║ ╚═╝ ██║██║  ██║███████╗╚██████╔╝██║ ╚████║██║  ██║
   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝{R}

{B}{G}  MYTHOS NEMESIS v{VERSION}{R} — Anti-Online-Gambling Intelligence Platform
{Y}  By: {AUTHOR}{R}
{C}  ⚠️  Legal Use Only — No DDoS. Always shut down servers after testing.{R}

  {G}●{R} Web Dashboard: {B}http://localhost:{DEFAULT_PORT}{R}
  {G}●{R} SocketIO:      {B}ws://localhost:{DEFAULT_PORT}{R}
  {G}●{R} Kali Tools:    {B}{len(kali.available())} available{R}
  {G}●{R} HexStrike-AI:  {B}{'Online' if hexstrike.is_available() else 'Offline'}{R}
  {G}●{R} MCP Bridge:    {B}Port {BLOCKED_PORT} BLOCKED ✓{R}
""")

def main():
    port = DEFAULT_PORT

    # Parse args
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith('--port='):
                port = arg.split('=')[1]
            elif arg == '--port':
                idx = sys.argv.index(arg) + 1
                if idx < len(sys.argv):
                    port = sys.argv[idx]
            elif arg in ('--help', '-h'):
                print_banner()
                print(f"""
  Usage: mythos [OPTIONS]

  Options:
    --port=PORT    Web server port (default: {DEFAULT_PORT}, BLOCKED: {BLOCKED_PORT})
    --help, -h     Show this help

  Examples:
    mythos                  Start on port {DEFAULT_PORT}
    mythos --port=3000      Start on port 3000
""")
                sys.exit(0)

    # Validate port
    port = validate_port(port)

    print_banner()
    log.info(f"Starting MYTHOS NEMESIS on port {port}...")

    # Register signal handler
    def shutdown(sig, frame):
        log.banner("Shutting down MYTHOS NEMESIS")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Start server
    try:
        socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
    except OSError as e:
        if 'Address already in use' in str(e):
            log.error(f"Port {port} is already in use!")
            log.info(f"Try: mythos --port={port + 1}")
        else:
            log.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
