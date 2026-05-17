/* ============================================================
   MYTHOS NEMESIS v2.0 — Frontend JavaScript
   Log Rain Canvas | SocketIO | UI Logic
   By: ibnu qory nur fikri / Dorakula
   ============================================================ */

(function() {
    'use strict';

    // ============================================================
    // LOG RAIN CANVAS BACKGROUND
    // ============================================================
    const canvas = document.getElementById('logRainCanvas');
    const ctx = canvas.getContext('2d');
    let columns = [];
    let logChars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*<>{}[]|/\\~';
    let fontSize = 14;

    function initCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        const colCount = Math.floor(canvas.width / fontSize);
        columns = Array(colCount).fill(0).map(() => Math.random() * canvas.height / fontSize);
    }

    function drawLogRain() {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#00d4ff';
        ctx.font = fontSize + 'px JetBrains Mono, monospace';

        for (let i = 0; i < columns.length; i++) {
            const char = logChars[Math.floor(Math.random() * logChars.length)];
            const x = i * fontSize;
            const y = columns[i] * fontSize;
            ctx.globalAlpha = Math.random() * 0.5 + 0.1;
            ctx.fillText(char, x, y);
            if (y > canvas.height && Math.random() > 0.975) {
                columns[i] = 0;
            }
            columns[i]++;
        }
        ctx.globalAlpha = 1;
        requestAnimationFrame(drawLogRain);
    }

    window.addEventListener('resize', initCanvas);
    initCanvas();
    drawLogRain();

    // ============================================================
    // SOCKETIO CONNECTION
    // ============================================================
    const socket = io();

    socket.on('connect', () => {
        console.log('[MYTHOS] Connected to server');
        addTerminalLine('system', 'Connection established to MYTHOS NEMESIS server');
        // Load initial data
        socket.emit('get_tools');
        loadScans();
        loadBlocklist();
        checkHexStrike();
    });

    socket.on('disconnect', () => {
        console.log('[MYTHOS] Disconnected from server');
        addTerminalLine('error', 'Connection lost! Attempting reconnect...');
    });

    socket.on('connected', (data) => {
        addTerminalLine('system', `MYTHOS NEMESIS v${data.version} — By: ${data.author}`);
    });

    socket.on('stats_update', (data) => {
        updateStats(data);
    });

    socket.on('log_event', (data) => {
        addLogEntry(data.level, data.message);
        addTerminalLine(data.level, data.message);
    });

    socket.on('scan_started', (data) => {
        showScanProgress(data);
        addTerminalLine('success', `Scan started: ${data.scan_id} → ${data.target} (${data.scan_type})`);
    });

    socket.on('scan_completed', (data) => {
        onScanCompleted(data);
    });

    socket.on('scan_error', (data) => {
        addTerminalLine('error', `Scan error: ${data.error}`);
        updatePhaseStatus('error');
    });

    socket.on('scan_stopped', (data) => {
        addTerminalLine('warning', `Scan stopped: ${data.scan_id}`);
    });

    socket.on('scan_results', (data) => {
        displayIntelResults(data);
    });

    socket.on('tools_list', (data) => {
        renderToolsGrid(data.tools);
    });

    socket.on('tool_result', (data) => {
        document.getElementById('toolOutput').textContent = data.output || 'No output';
    });

    socket.on('tool_error', (data) => {
        document.getElementById('toolOutput').textContent = `[ERROR] ${data.error}`;
    });

    socket.on('blocklist_data', (data) => {
        renderBlocklist(data.entries);
    });

    socket.on('blocklist_updated', (data) => {
        addTerminalLine('success', `Blocklist updated: ${data.domain} ${data.action}`);
        loadBlocklist();
    });

    // ============================================================
    // NAVIGATION
    // ============================================================
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const page = item.dataset.page;
            // Update active nav
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            item.classList.add('active');
            // Show page
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.getElementById('page-' + page).classList.add('active');
        });
    });

    // ============================================================
    // STATS
    // ============================================================
    function updateStats(data) {
        document.getElementById('statScans').textContent = data.scans || 0;
        document.getElementById('statIntel').textContent = data.intelligence || 0;
        document.getElementById('statEvidence').textContent = data.evidence || 0;
        document.getElementById('statBlocked').textContent = data.blocked || 0;
    }

    function loadStats() {
        fetch('/api/stats')
            .then(r => r.json())
            .then(data => updateStats(data))
            .catch(err => console.error('Stats error:', err));
    }

    // ============================================================
    // SCANS
    // ============================================================
    function loadScans() {
        fetch('/api/scans')
            .then(r => r.json())
            .then(data => renderScansTable(data))
            .catch(err => console.error('Scans error:', err));
        loadStats();
    }

    function renderScansTable(scans) {
        const body = document.getElementById('recentScansBody');
        if (!scans || scans.length === 0) {
            body.innerHTML = '<tr><td colspan="6" class="empty-state">No scans yet. Start a new scan to begin.</td></tr>';
            return;
        }
        body.innerHTML = scans.map(s => `
            <tr onclick="loadScanDetail('${s.id}')" style="cursor:pointer">
                <td><span style="color:var(--accent-cyan)">${s.id}</span></td>
                <td>${escapeHtml(s.target)}</td>
                <td><span class="phase-badge detect">${s.scan_type}</span></td>
                <td><span style="color:${statusColor(s.status)}">${s.status}</span></td>
                <td>${s.started_at || '—'}</td>
                <td>${s.result_count || 0}</td>
            </tr>
        `).join('');

        // Also update intel scan select
        const sel = document.getElementById('intelScanSelect');
        sel.innerHTML = '<option value="">Select a scan...</option>' +
            scans.map(s => `<option value="${s.id}">${s.id} — ${s.target}</option>`).join('');
    }

    function statusColor(status) {
        const colors = { running: 'var(--accent-cyan)', completed: 'var(--accent-green)',
                        error: 'var(--accent-red)', stopped: 'var(--accent-yellow)' };
        return colors[status] || 'var(--text-dim)';
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Make loadScanDetail available globally
    window.loadScanDetail = function(scanId) {
        fetch(`/api/scans/${scanId}`)
            .then(r => r.json())
            .then(data => displayIntelResults({ scan_id: scanId, ...data }))
            .catch(err => console.error('Detail error:', err));
        // Switch to intel page
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        document.querySelector('[data-page="intel"]').classList.add('active');
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById('page-intel').classList.add('active');
        // Set select
        document.getElementById('intelScanSelect').value = scanId;
    };

    // ============================================================
    // SCAN CONTROLS
    // ============================================================
    document.getElementById('btnStartScan').addEventListener('click', startScan);
    document.getElementById('btnQuickScan').addEventListener('click', quickScan);
    document.getElementById('btnStopScan').addEventListener('click', stopScan);

    function startScan() {
        const target = document.getElementById('scanTarget').value.trim();
        const scanType = document.getElementById('scanType').value;
        if (!target) {
            alert('Please enter a target');
            return;
        }
        const phases = [];
        document.querySelectorAll('.phase-toggle input:checked').forEach(cb => {
            phases.push(cb.value);
        });

        socket.emit('start_scan', { target, scan_type: scanType, phases: phases.length ? phases : null });
        document.getElementById('scanProgress').style.display = 'block';
        document.getElementById('activeScanTarget').textContent = target;
    }

    function quickScan() {
        const target = document.getElementById('scanTarget').value.trim();
        if (!target) {
            alert('Please enter a target');
            return;
        }
        socket.emit('quick_scan', { target });
        document.getElementById('scanProgress').style.display = 'block';
        document.getElementById('activeScanTarget').textContent = target;
    }

    function stopScan() {
        const scanId = document.getElementById('activeScanId').textContent;
        if (scanId && scanId !== '—') {
            socket.emit('stop_scan', { scan_id: scanId });
        }
    }

    function showScanProgress(data) {
        document.getElementById('scanProgress').style.display = 'block';
        document.getElementById('activeScanId').textContent = data.scan_id;
        document.getElementById('activeScanTarget').textContent = data.target;
        // Reset phases
        document.querySelectorAll('.kc-phase').forEach(p => {
            p.classList.remove('running', 'completed', 'error');
            p.querySelector('.kc-status').textContent = '—';
        });
        document.getElementById('scanLogStream').innerHTML = '';
    }

    function onScanCompleted(data) {
        addTerminalLine('success', `Scan completed: ${data.scan_id} — ${data.target}`);
        // Mark all phases as completed
        document.querySelectorAll('.kc-phase').forEach(p => {
            if (p.querySelector('.kc-status').textContent !== '—') {
                p.classList.add('completed');
                p.querySelector('.kc-status').textContent = 'Done';
            }
        });
        loadScans();
    }

    function updatePhaseStatus(phase, status) {
        // This is called from log events to track which phase is running
        const phaseMap = {
            'DETECT': 0, 'TRACE': 1, 'STRANGLE': 2, 'BLOCK': 3, 'MONITOR': 4
        };
        const phases = document.querySelectorAll('.kc-phase');
        const idx = phaseMap[phase];
        if (idx !== undefined && phases[idx]) {
            if (status === 'running') {
                phases[idx].classList.add('running');
                phases[idx].querySelector('.kc-status').textContent = 'Running...';
                // Mark previous as completed
                for (let i = 0; i < idx; i++) {
                    phases[i].classList.remove('running');
                    phases[i].classList.add('completed');
                    phases[i].querySelector('.kc-status').textContent = 'Done';
                }
            }
        }
    }

    // ============================================================
    // INTELLIGENCE DISPLAY
    // ============================================================
    document.getElementById('intelScanSelect').addEventListener('change', function() {
        const scanId = this.value;
        if (scanId) {
            socket.emit('get_scan_results', { scan_id: scanId });
        }
    });

    function displayIntelResults(data) {
        const intel = data.intelligence || [];
        const evidence = data.evidence || [];
        const layerCounts = {};

        intel.forEach(item => {
            const layer = item.layer;
            if (!layerCounts[layer]) layerCounts[layer] = 0;
            layerCounts[layer]++;
        });

        // Update layer counts
        const layerMap = {
            'L1_DOMAIN': 'L1', 'L2_CONTENT': 'L2', 'L3_INFRA': 'L3',
            'L4_FINANCIAL': 'L4', 'L5_NETWORK': 'L5', 'L6_HISTORICAL': 'L6'
        };

        Object.keys(layerMap).forEach(layer => {
            const key = layerMap[layer];
            const count = layerCounts[layer] || 0;
            // Dashboard layer counts
            const dashEl = document.getElementById('layer' + key);
            if (dashEl) dashEl.textContent = count;
            // Intel page counts
            const intelCountEl = document.getElementById('intelCount' + key);
            if (intelCountEl) intelCountEl.textContent = count;
        });

        // Populate intel layers
        Object.keys(layerMap).forEach(layer => {
            const key = layerMap[layer];
            const body = document.getElementById('intelBody' + key);
            const items = intel.filter(i => i.layer === layer);
            if (items.length === 0) {
                body.innerHTML = '<div class="empty-state">No data</div>';
            } else {
                body.innerHTML = items.map(i => `
                    <div class="intel-item">
                        <span class="intel-key">${escapeHtml(i.category)}</span>
                        <span class="intel-value">${escapeHtml(i.value_field || i.key_field)}</span>
                        <span class="intel-source">${i.source || ''}</span>
                    </div>
                `).join('');
            }
        });

        // Evidence
        const evList = document.getElementById('evidenceList');
        if (evidence.length === 0) {
            evList.innerHTML = '<div class="empty-state">No evidence collected yet</div>';
        } else {
            evList.innerHTML = evidence.map(e => `
                <div class="evidence-item">
                    <div class="evidence-title">${escapeHtml(e.title)}</div>
                    <div class="evidence-desc">${escapeHtml(e.description)}</div>
                    <div class="evidence-hash">SHA256: ${e.hash_sha256 ? e.hash_sha256.substring(0, 32) + '...' : 'N/A'}</div>
                </div>
            `).join('');
        }
    }

    // ============================================================
    // TOOLS
    // ============================================================
    function renderToolsGrid(tools) {
        const grid = document.getElementById('toolsGrid');
        document.getElementById('toolsCount').textContent = tools.length + ' available';
        if (tools.length === 0) {
            grid.innerHTML = '<div class="empty-state">No Kali tools detected</div>';
            return;
        }
        grid.innerHTML = tools.map(t => `
            <div class="tool-chip" onclick="selectTool('${t}')">${t}</div>
        `).join('');
    }

    window.selectTool = function(tool) {
        document.getElementById('manualTool').value = tool;
    };

    document.getElementById('btnRunTool').addEventListener('click', () => {
        const tool = document.getElementById('manualTool').value.trim();
        const target = document.getElementById('manualTarget').value.trim();
        const args = document.getElementById('manualArgs').value.trim();
        if (!tool || !target) {
            alert('Tool and target are required');
            return;
        }
        document.getElementById('toolOutput').textContent = 'Running...';
        socket.emit('run_tool', { tool, target, args });
    });

    // ============================================================
    // BLOCKLIST
    // ============================================================
    function loadBlocklist() {
        socket.emit('get_blocklist');
    }

    function renderBlocklist(entries) {
        const body = document.getElementById('blocklistBody');
        if (!entries || entries.length === 0) {
            body.innerHTML = '<tr><td colspan="5" class="empty-state">No blocked domains yet</td></tr>';
            return;
        }
        body.innerHTML = entries.map(e => `
            <tr>
                <td style="color:var(--accent-red)">${escapeHtml(e.domain)}</td>
                <td>${escapeHtml(e.ip_address || '—')}</td>
                <td>${escapeHtml(e.reason)}</td>
                <td>${e.added_at || '—'}</td>
                <td>${escapeHtml(e.source)}</td>
            </tr>
        `).join('');
    }

    document.getElementById('btnAddBlock').addEventListener('click', () => {
        const domain = document.getElementById('blockDomain').value.trim();
        const ip = document.getElementById('blockIP').value.trim();
        const reason = document.getElementById('blockReason').value.trim();
        if (!domain) {
            alert('Domain is required');
            return;
        }
        socket.emit('add_blocklist', { domain, ip, reason });
        document.getElementById('blockDomain').value = '';
        document.getElementById('blockIP').value = '';
        document.getElementById('blockReason').value = '';
    });

    document.getElementById('btnRefreshBlocklist').addEventListener('click', loadBlocklist);

    document.getElementById('btnExportBlocklist').addEventListener('click', () => {
        window.open('/api/blocklist/export', '_blank');
    });

    // ============================================================
    // HEXSTRIKE STATUS
    // ============================================================
    function checkHexStrike() {
        fetch('/api/hexstrike/status')
            .then(r => r.json())
            .then(data => {
                const el = document.getElementById('hexstrikeStatus');
                if (data.available || data.status === 'standby') {
                    const statusText = data.status === 'standby' ? 'Standby' : 'Online';
                    el.innerHTML = '<span class="status-dot online"></span><span>HexStrike: ' + statusText + '</span>';
                } else {
                    el.innerHTML = '<span class="status-dot offline"></span><span>HexStrike: Offline</span>';
                }
            })
            .catch(() => {});
    }

    // ============================================================
    // LOG ENTRIES
    // ============================================================
    function addLogEntry(level, message) {
        const stream = document.getElementById('dashboardLogStream');
        const entry = document.createElement('div');
        entry.className = 'log-entry ' + level;
        const ts = new Date().toLocaleTimeString();
        entry.textContent = `[${ts}] ${message}`;
        stream.appendChild(entry);
        stream.scrollTop = stream.scrollHeight;

        // Also add to scan log stream if visible
        const scanLog = document.getElementById('scanLogStream');
        if (scanLog) {
            const scanEntry = document.createElement('div');
            scanEntry.className = 'log-entry ' + level;
            scanEntry.textContent = `[${ts}] ${message}`;
            scanLog.appendChild(scanEntry);
            scanLog.scrollTop = scanLog.scrollHeight;
        }

        // Parse log messages for kill chain phase tracking
        if (message.includes('KILL CHAIN')) {
            const phaseMatch = message.match(/KILL CHAIN — (\w+):/);
            if (phaseMatch) {
                updatePhaseStatus(phaseMatch[1], 'running');
            }
        }
    }

    // ============================================================
    // TERMINAL
    // ============================================================
    function addTerminalLine(type, message) {
        const body = document.getElementById('terminalBody');
        const line = document.createElement('div');
        line.className = 'terminal-line ' + type;
        const ts = new Date().toLocaleTimeString();
        const prefix = type === 'system' ? '◉ ' :
                       type === 'success' ? '✓ ' :
                       type === 'error' ? '✗ ' :
                       type === 'warning' ? '⚠ ' : '… ';
        line.textContent = `[${ts}] ${prefix}${message}`;
        body.appendChild(line);
        body.scrollTop = body.scrollHeight;
    }

    document.getElementById('btnClearLogs').addEventListener('click', () => {
        document.getElementById('terminalBody').innerHTML = `
            <div class="terminal-line system">Terminal cleared</div>
            <div class="terminal-line system">─────────────────────────────────────</div>
        `;
    });

    // ============================================================
    // INITIAL LOAD
    // ============================================================
    loadStats();
    setInterval(loadStats, 10000);

    // Enter key on scan target
    document.getElementById('scanTarget').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') startScan();
    });



    // ============================================================
    // IP TRACKER — Pelacak Lokasi IP Address
    // ============================================================
    const ipTrackTarget = document.getElementById('ipTrackTarget');
    const btnTrackIP = document.getElementById('btnTrackIP');
    const btnQuickLookup = document.getElementById('btnQuickLookup');
    const btnBatchTrack = document.getElementById('btnBatchTrack');
    const ipBatchTargets = document.getElementById('ipBatchTargets');
    const ipQuickResult = document.getElementById('ipQuickResult');
    const ipTrackResults = document.getElementById('ipTrackResults');
    const ipTrackLoading = document.getElementById('ipTrackLoading');
    const btnCopyReport = document.getElementById('btnCopyReport');

    // Track IP button
    if (btnTrackIP) {
        btnTrackIP.addEventListener('click', () => {
            const target = ipTrackTarget.value.trim();
            if (!target) {
                addTerminalLine('error', 'Please enter an IP address or domain');
                return;
            }
            ipQuickResult.style.display = 'none';
            ipTrackResults.style.display = 'none';
            ipTrackLoading.style.display = 'block';
            addTerminalLine('info', `Starting IP tracking: ${target}`);
            socket.emit('track_ip', { target: target });
        });
    }

    // Quick Lookup button
    if (btnQuickLookup) {
        btnQuickLookup.addEventListener('click', () => {
            const target = ipTrackTarget.value.trim();
            if (!target) {
                addTerminalLine('error', 'Please enter an IP address or domain');
                return;
            }
            addTerminalLine('info', `Quick IP lookup: ${target}`);
            socket.emit('ip_quick_lookup', { target: target });
        });
    }

    // Batch Track button
    if (btnBatchTrack) {
        btnBatchTrack.addEventListener('click', () => {
            const targetsText = ipBatchTargets.value.trim();
            if (!targetsText) {
                addTerminalLine('error', 'Please enter IPs/domains for batch tracking');
                return;
            }
            const targets = targetsText.split('\n').map(t => t.trim()).filter(t => t);
            addTerminalLine('info', `Batch tracking ${targets.length} target(s)`);
            socket.emit('track_ip_batch', { targets: targets });
        });
    }

    // Copy Report button
    if (btnCopyReport) {
        btnCopyReport.addEventListener('click', () => {
            const report = document.getElementById('ipAuthorityReport');
            if (report) {
                const text = report.innerText;
                navigator.clipboard.writeText(text).then(() => {
                    addTerminalLine('success', 'Authority report copied to clipboard');
                }).catch(() => {
                    // Fallback
                    const textarea = document.createElement('textarea');
                    textarea.value = text;
                    document.body.appendChild(textarea);
                    textarea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textarea);
                    addTerminalLine('success', 'Authority report copied to clipboard');
                });
            }
        });
    }

    // SocketIO handlers for IP Tracker
    socket.on('ip_track_started', (data) => {
        addTerminalLine('success', `IP tracking started: ${data.target}`);
        const statusEl = document.getElementById('ipTrackStatus');
        if (statusEl) statusEl.textContent = `Tracking ${data.target}...`;
    });

    socket.on('ip_track_results', (data) => {
        ipTrackLoading.style.display = 'none';
        ipTrackResults.style.display = 'block';
        const r = data.results;
        addTerminalLine('success', `IP tracking complete: ${data.target}`);

        // Risk Level
        const riskBanner = document.getElementById('ipRiskBanner');
        const riskLevel = document.getElementById('ipRiskLevel');
        if (riskLevel && r.risk_level) {
            riskLevel.textContent = r.risk_level;
            riskBanner.className = 'risk-banner risk-' + r.risk_level.toLowerCase();
        }

        // Target Info
        setText('ipTarget', r.target);
        setText('ipResolved', r.resolved_ip);
        setText('ipReverseDNS', r.reverse_dns || 'N/A');

        // Geo Location
        const geo = r.geo_location || {};
        setText('ipContinent', geo.continent || 'N/A');
        setText('ipCountry', `${geo.country || 'N/A'} (${geo.country_code || ''})`);
        setText('ipRegion', geo.region || 'N/A');
        setText('ipCity', geo.city || 'N/A');
        setText('ipCoords', `${geo.lat || '?'}, ${geo.lon || '?'}`);
        setText('ipTimezone', geo.timezone || 'N/A');

        // Map
        const mapInfo = document.getElementById('ipMapInfo');
        const mapCoords = document.getElementById('ipMapCoords');
        if (mapInfo && geo.city) {
            mapInfo.textContent = `${geo.city}, ${geo.region || ''}, ${geo.country || ''}`;
        }
        if (mapCoords && geo.lat) {
            mapCoords.textContent = `Lat: ${geo.lat} | Lon: ${geo.lon} | Timezone: ${geo.timezone || 'N/A'}`;
        }

        // ISP & ASN
        const asn = r.asn_info || {};
        setText('ipISP', asn.isp || 'N/A');
        setText('ipOrg', asn.org || 'N/A');
        setText('ipAS', asn.as || 'N/A');
        setText('ipASName', asn.asname || 'N/A');

        // Hosting Provider
        const hosting = r.hosting_provider || {};
        setText('ipHostingName', hosting.detected ? hosting.name : 'Not detected');
        setText('ipHostingType', hosting.type || 'N/A');
        setText('ipHostingAbuse', hosting.abuse_email || 'N/A');
        setText('ipHostingURL', hosting.report_url || 'N/A');

        // VPN/Proxy
        const vpn = r.vpn_proxy_detection || {};
        const vpnStatus = document.getElementById('ipVPNStatus');
        if (vpnStatus) {
            vpnStatus.textContent = vpn.is_vpn_proxy ? 'YES — ' + (vpn.type || '') : 'NO';
            vpnStatus.style.color = vpn.is_vpn_proxy ? 'var(--accent-red)' : 'var(--accent-green)';
        }
        setText('ipVPNType', vpn.type || 'N/A');
        setText('ipVPNConfidence', vpn.confidence ? `${(vpn.confidence * 100).toFixed(0)}%` : 'N/A');

        // WHOIS
        const whois = r.whois_data || {};
        setText('ipWhoisNet', whois.net_name || 'N/A');
        setText('ipWhoisOrg', whois.organization || 'N/A');
        setText('ipWhoisCountry', whois.country || 'N/A');
        setText('ipWhoisRange', whois.ip_range || 'N/A');
        setText('ipWhoisAbuse', whois.abuse_contact || 'N/A');

        // Ports
        const nmap = r.nmap_services || {};
        const portsBody = document.getElementById('ipPortsBody');
        const ports = nmap.ports || [];
        if (portsBody && ports.length > 0) {
            portsBody.innerHTML = ports.map(p => 
                `<tr><td style="color:var(--accent-cyan)">${escapeHtml(p.port || '')}</td><td>${escapeHtml(p.state || '')}</td><td>${escapeHtml(p.service || '')}</td><td>${escapeHtml(p.version || '')}</td></tr>`
            ).join('');
        } else if (portsBody) {
            portsBody.innerHTML = '<tr><td colspan="4" class="empty-state">No open ports detected</td></tr>';
        }
        setText('ipOSGuess', nmap.os_guess || 'N/A');

        // Traceroute
        const trList = document.getElementById('ipTracerouteList');
        const hops = r.traceroute || [];
        if (trList && hops.length > 0) {
            trList.innerHTML = hops.map(h => 
                `<div class="traceroute-hop"><span class="hop-num">Hop ${escapeHtml(String(h.hop || '?'))}</span><span class="hop-ip">${escapeHtml(h.ip || '???')}</span></div>`
            ).join('');
        } else if (trList) {
            trList.innerHTML = '<div class="empty-state">Traceroute not available</div>';
        }

        // Abuse Contacts
        const abuseEl = document.getElementById('ipAbuseContacts');
        const contacts = r.abuse_contacts || [];
        if (abuseEl && contacts.length > 0) {
            abuseEl.innerHTML = contacts.map(c => 
                `<div class="abuse-contact-item glass">
                    <div class="abuse-contact-name">${escapeHtml(c.name || '')}</div>
                    <div class="abuse-contact-type">${escapeHtml(c.type || '')}</div>
                    <div class="abuse-contact-email">${c.email ? '<a href="mailto:' + escapeHtml(c.email) + '">' + escapeHtml(c.email) + '</a>' : 'N/A'}</div>
                    ${c.report_url ? '<div class="abuse-contact-url"><a href="' + escapeHtml(c.report_url) + '" target="_blank">' + escapeHtml(c.report_url) + '</a></div>' : ''}
                </div>`
            ).join('');
        } else if (abuseEl) {
            abuseEl.innerHTML = '<div class="empty-state">No abuse contacts found</div>';
        }

        // Authority Report
        const reportEl = document.getElementById('ipAuthorityReport');
        if (reportEl && r.authority_report) {
            reportEl.innerHTML = '<pre>' + escapeHtml(r.authority_report) + '</pre>';
        }
    });

    socket.on('ip_quick_result', (data) => {
        ipQuickResult.style.display = 'block';
        const s = data.summary;
        setText('quickIP', s.ip || 'N/A');
        setText('quickLocation', s.location || 'N/A');
        setText('quickCoords', s.coordinates || 'N/A');
        setText('quickISP', s.isp || 'N/A');
        setText('quickCountry', s.country_code || 'N/A');
        const hostingEl = document.getElementById('quickHosting');
        if (hostingEl) {
            let hostText = 'No';
            if (s.is_hosting) hostText = 'Yes — Hosting';
            else if (s.is_proxy) hostText = 'Yes — Proxy';
            hostingEl.textContent = hostText;
            hostingEl.style.color = (s.is_hosting || s.is_proxy) ? 'var(--accent-red)' : 'var(--accent-green)';
        }
        addTerminalLine('success', `Quick lookup: ${s.ip} → ${s.location} (${s.isp})`);
    });

    socket.on('ip_track_batch_results', (data) => {
        addTerminalLine('success', `Batch tracking complete: ${data.targets_count} target(s)`);
        // Show first result
        if (data.results && data.results.length > 0) {
            socket.emit('track_ip', { target: data.results[0].target });
        }
    });

    socket.on('ip_track_error', (data) => {
        ipTrackLoading.style.display = 'none';
        addTerminalLine('error', `IP tracking error: ${data.error}`);
    });

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value || 'N/A';
    }


})();
// ============================================================
// HEXSTRIKE-AI v6.0 Handler
// ============================================================

const HexStrike = {
    tools: [],
    categories: {},

    init() {
        // SocketIO events
        socket.on("hexstrike_health_result", (data) => {
            this.updateStatus(data);
        });
        socket.on("hexstrike_tool_result", (data) => {
            this.appendOutput(data);
        });
        socket.on("hexstrike_scan_result", (data) => {
            this.appendOutput(data);
        });
        socket.on("hexstrike_bugbounty_result", (data) => {
            this.appendOutput(data);
        });
        socket.on("hexstrike_intel_result", (data) => {
            this.appendOutput(data);
        });

        // Button handlers
        document.getElementById("btnRefreshHS").addEventListener("click", () => this.checkHealth());
        document.getElementById("btnRunHSTool").addEventListener("click", () => this.runTool());
        document.getElementById("btnClearHSOutput").addEventListener("click", () => this.clearOutput());

        // Quick action buttons
        document.querySelectorAll("[data-hs-action]").forEach(btn => {
            btn.addEventListener("click", () => this.quickAction(btn.dataset.hsAction));
        });

        // Initial check
        this.checkHealth();
        this.loadTools();
    },

    checkHealth() {
        socket.emit("hexstrike_health");
        fetch("/api/hexstrike/status")
            .then(r => r.json())
            .then(data => {
                const badge = document.getElementById("hexstrikeBadge");
                const statusEl = document.getElementById("hexstrikeStatus");
                if (data.available || data.status === "standby") {
                    badge.textContent = "ONLINE";
                    badge.className = "badge badge-success";
                    if (statusEl) {
                        statusEl.querySelector(".status-dot").className = "status-dot online";
                        statusEl.querySelector("span:last-child").textContent = "HexStrike: Online";
                    }
                } else {
                    badge.textContent = "OFFLINE";
                    badge.className = "badge badge-danger";
                    if (statusEl) {
                        statusEl.querySelector(".status-dot").className = "status-dot offline";
                        statusEl.querySelector("span:last-child").textContent = "HexStrike: Offline";
                    }
                }
                document.getElementById("hsToolCount").textContent = data.total_tools || "--";
                document.getElementById("hsCatCount").textContent = data.categories || "--";
                if (data.health) {
                    document.getElementById("hsAvailCount").textContent = data.health.total_tools_available || "--";
                    document.getElementById("hsVersion").textContent = data.health.version || "--";
                }
            })
            .catch(() => {
                document.getElementById("hexstrikeBadge").textContent = "ERROR";
                document.getElementById("hexstrikeBadge").className = "badge badge-danger";
            });
    },

    loadTools() {
        fetch("/api/hexstrike/tools")
            .then(r => r.json())
            .then(data => {
                this.tools = data.all_tools || [];
                this.categories = data.categories || {};
                this.populateToolSelect();
                this.renderCategories();
            })
            .catch(() => {});
    },

    populateToolSelect() {
        const select = document.getElementById("hsToolSelect");
        select.innerHTML = "<option value=\"\">Select Tool...</option>";
        this.tools.forEach(tool => {
            const opt = document.createElement("option");
            opt.value = tool;
            opt.textContent = tool;
            select.appendChild(opt);
        });
    },

    renderCategories() {
        const container = document.getElementById("hsCategories");
        container.innerHTML = "";
        for (const [cat, tools] of Object.entries(this.categories)) {
            const div = document.createElement("div");
            div.className = "hs-category";
            div.innerHTML = `
                <h5>${cat} <span class="badge">${tools.length}</span></h5>
                <div class="hs-tool-list">${tools.map(t => `<span class="hs-tool-tag" data-tool="${t}">${t}</span>`).join("")}</div>
            `;
            container.appendChild(div);
        }
        // Click handler for tool tags
        container.querySelectorAll(".hs-tool-tag").forEach(tag => {
            tag.addEventListener("click", () => {
                document.getElementById("hsToolSelect").value = tag.dataset.tool;
                document.getElementById("hsTargetInput").focus();
            });
        });
    },

    runTool() {
        const tool = document.getElementById("hsToolSelect").value;
        const target = document.getElementById("hsTargetInput").value.trim();
        const optionsStr = document.getElementById("hsOptionsInput").value.trim();
        if (!tool || !target) {
            this.appendOutput({error: "Tool and target are required"});
            return;
        }
        let options = {};
        if (optionsStr) {
            try { options = JSON.parse(optionsStr); } catch(e) { options = {extra: optionsStr}; }
        }
        this.appendOutput({system: `Running ${tool} -> ${target}...`});
        socket.emit("hexstrike_run_tool", {tool, target, options});
    },

    quickAction(action) {
        const target = document.getElementById("hsTargetInput").value.trim();
        if (!target) {
            this.appendOutput({error: "Enter a target first"});
            document.getElementById("hsTargetInput").focus();
            return;
        }
        if (["analyze","smart_scan","tech_detect","tools_select"].includes(action)) {
            const type = action === "smart_scan" ? "smart_scan" : action;
            if (action === "smart_scan") {
                socket.emit("hexstrike_smart_scan", {target, objective: "comprehensive"});
            } else {
                socket.emit("hexstrike_intelligence", {target, type: action});
            }
        } else {
            socket.emit("hexstrike_bugbounty", {target, workflow: action});
        }
        this.appendOutput({system: `Quick action: ${action} -> ${target}...`});
    },

    appendOutput(data) {
        const output = document.getElementById("hsOutput");
        if (!output) return;
        const line = document.createElement("div");
        if (data.error) {
            line.className = "terminal-line error";
            line.textContent = `[ERROR] ${data.error}`;
        } else if (data.system) {
            line.className = "terminal-line system";
            line.textContent = data.system;
        } else if (data.result) {
            line.className = "terminal-line success";
            line.textContent = typeof data.result === "string" ? data.result : JSON.stringify(data.result, null, 2);
        } else {
            line.className = "terminal-line";
            line.textContent = JSON.stringify(data, null, 2);
        }
        output.appendChild(line);
        output.scrollTop = output.scrollHeight;
    },

    clearOutput() {
        document.getElementById("hsOutput").innerHTML = "<div class=\"terminal-line system\">Output cleared</div>";
    }
};
HexStrike.init();
