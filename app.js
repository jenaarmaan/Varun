// Project Varun Frontend State Management
const state = {
    mode: 'sandbox', // 'sandbox' (mock) or 'production' (live api)
    activeTab: 'overview',
    selectedDistrict: null,
    isSyncing: false,
    isChatting: false,
    lastSyncTime: null,
    syncedNodesCount: 0,
    districts: {
        district_29: {
            id: "district_29",
            name: "Mysuru",
            state: "Karnataka",
            population: "3,001,000",
            source: "OpenMeteo Sync",
            geom: "POLYGON((76.3 12.1, 76.8 12.1, 76.8 12.6, 76.3 12.6, 76.3 12.1))",
            riskScore: 88,
            weather: "Heavy Rain (29°C)",
            vulnerability: "Critical assets downstream of Krishna Raja Sagara reservoir (Mysuru Public School, Mysuru Power Grid) are at extreme risk of inundation due to the reservoir reaching its maximum spill limit (124.8 ft)."
        },
        district_21: {
            id: "district_21",
            name: "Khordha (Bhubaneswar)",
            state: "Odisha",
            population: "2,251,000",
            source: "IMD Bulletin PDF",
            geom: "POLYGON((85.5 20.1, 85.9 20.1, 85.9 20.5, 85.5 20.5, 85.5 20.1))",
            riskScore: 62,
            weather: "Thunderstorms (33°C)",
            vulnerability: "Bhubaneswar General Hospital is currently marked safe with stable drainage in the Mahanadi basin. Minor storm water accumulation on city arterial roads is expected."
        }
    }
};

// Console logger utility
function logConsole(message, type = 'info') {
    const consoleLogs = document.getElementById('console-logs');
    if (!consoleLogs) return;

    const timestamp = new Date().toISOString().split('T')[1].slice(0, 8);
    const line = document.createElement('div');
    line.className = `log-line ${type}`;
    line.innerText = `[${timestamp}] [${type.toUpperCase()}] ${message}`;
    
    consoleLogs.appendChild(line);
    consoleLogs.scrollTop = consoleLogs.scrollHeight;
}

// Initialize Application
window.addEventListener('DOMContentLoaded', () => {
    logConsole("Project Varun UI Console Ready.");
    logConsole("Defaulting to Sandbox (Mock Data) Mode to allow immediate evaluation.");
    
    // Set initial active tab
    switchTab('overview');
});

// Tab Switching Logic
function switchTab(tabId) {
    state.activeTab = tabId;
    
    // Update button states
    const tabs = ['overview', 'chat', 'ingest'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab-${t}`);
        const content = document.getElementById(`content-${t}`);
        
        if (t === tabId) {
            btn.classList.add('active');
            btn.setAttribute('aria-selected', 'true');
            content.classList.add('active');
        } else {
            btn.classList.remove('active');
            btn.setAttribute('aria-selected', 'false');
            content.classList.remove('active');
        }
    });

    logConsole(`Switched active tab workspace to: ${tabId.toUpperCase()}`);
}

// Mode Selection Toggle (Sandbox vs Production)
function toggleMode() {
    const toggle = document.getElementById('mode-toggle');
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const chatEngineSubtext = document.getElementById('chat-engine-subtext');

    if (toggle.checked) {
        state.mode = 'sandbox';
        statusDot.className = 'status-dot online';
        statusText.innerText = 'Sandbox Active';
        chatEngineSubtext.innerText = 'Sandbox Mode (Mocked Grounding Context)';
        logConsole("Mode changed: Sandbox Mode is active. API requests are mocked.", "warning");
    } else {
        state.mode = 'production';
        statusDot.className = 'status-dot online';
        statusText.innerText = 'Production Active';
        chatEngineSubtext.innerText = 'Live API Mode (Connected to Vercel FastAPI)';
        logConsole("Mode changed: Production Mode is active. API requests route to Vercel backend.", "success");
        
        // Ping health check to verify backend online
        pingBackendHealth();
    }
}

// Live API: Ping health check
async function pingBackendHealth() {
    logConsole("Pinging live FastAPI health check at /api/v1/health...");
    try {
        const response = await fetch('/health'); // or /api/v1/health depending on paths, FastAPI has it under /health in main.py
        if (response.ok) {
            const data = await response.json();
            logConsole(`Backend Online! Status: ${data.status}, Env: ${data.environment}`, "success");
        } else {
            // Try /api/v1 prefix fallback
            const fallbackResponse = await fetch('/api/v1/health');
            if (fallbackResponse.ok) {
                const data = await fallbackResponse.json();
                logConsole(`Backend Online (V1)! Status: ${data.status}, Env: ${data.environment}`, "success");
            } else {
                throw new Error("HTTP failure");
            }
        }
    } catch (err) {
        logConsole("FastAPI Backend unreachable or databases not provisioned yet. Operating in Production mode may yield connection errors.", "error");
    }
}

// District Node Selection
function selectDistrict(districtId) {
    state.selectedDistrict = districtId;
    
    // Update map card active styles
    document.getElementById('district-29-card').classList.remove('active');
    document.getElementById('district-21-card').classList.remove('active');
    
    const selectedCard = document.getElementById(`${districtId}-card`);
    if (selectedCard) selectedCard.classList.add('active');

    // Update details panel
    const placeholder = document.getElementById('panel-placeholder');
    const details = document.getElementById('panel-details');
    
    placeholder.classList.add('hidden');
    details.classList.remove('hidden');

    const distData = state.districts[districtId];
    document.getElementById('detail-name').innerText = distData.name;
    document.getElementById('detail-lgd').innerText = distData.id;
    document.getElementById('detail-state').innerText = distData.state;
    document.getElementById('detail-pop').innerText = distData.population;
    document.getElementById('detail-source').innerText = distData.source;
    document.getElementById('detail-geom').innerText = distData.geom;
    document.getElementById('detail-vulnerability').innerText = distData.vulnerability;

    // Set badge warning text based on risk
    const badge = document.getElementById('detail-badge');
    const riskPercent = distData.riskScore;
    
    if (riskPercent > 80) {
        badge.className = 'badge warning';
        badge.innerText = 'Danger Warning';
        badge.style.background = 'rgba(239, 68, 68, 0.15)';
        badge.style.color = 'var(--color-danger)';
        badge.style.borderColor = 'rgba(239, 68, 68, 0.25)';
    } else {
        badge.className = 'badge warning';
        badge.innerText = 'Amber warning';
        badge.style.background = 'rgba(245, 158, 11, 0.15)';
        badge.style.color = 'var(--color-warning)';
        badge.style.borderColor = 'rgba(245, 158, 11, 0.25)';
    }

    // Dynamic Risk Meter update
    const riskFill = document.getElementById('detail-risk-fill');
    const riskText = document.getElementById('detail-risk-text');
    riskFill.style.width = `${riskPercent}%`;
    riskText.innerText = `Risk score: ${riskPercent}%`;
    
    if (riskPercent >= 75) {
        riskFill.className = 'meter-fill danger-fill';
    } else if (riskPercent >= 50) {
        riskFill.className = 'meter-fill warning-fill';
    } else {
        riskFill.className = 'meter-fill';
    }

    // Dynamic Human Vulnerability Index (HVI) calculation
    const popVal = parseInt(distData.population.replace(/,/g, ''), 10) || 0;
    const riskScoreDec = riskPercent / 100.0;
    const scaleFactor = Math.min(popVal / 1000000.0, 1.0);
    const hviVal = riskScoreDec * (0.7 + 0.3 * scaleFactor);
    const hviPercent = Math.round(hviVal * 100);

    const hviFill = document.getElementById('detail-hvi-fill');
    const hviText = document.getElementById('detail-hvi-text');
    hviFill.style.width = `${hviPercent}%`;
    hviText.innerText = `HVI Score: ${hviVal.toFixed(2)} (${hviPercent}%)`;

    // Populate SOP Checklist dynamically
    const sopList = document.getElementById('detail-sop-list');
    sopList.innerHTML = '';
    let sops = [];
    if (riskPercent >= 75) {
        sops = [
            "Activate District Emergency Operations Center (DEOC) to 24/7 alert status.",
            "Initiate immediate evacuation plans for identified low-lying zones.",
            "Pre-position NDRF and SDRF rescue units.",
            "Activate emergency shelters and deploy dry food/medical resources.",
            "Trigger broadcast public warning alerts."
        ];
    } else if (riskPercent >= 50) {
        sops = [
            "Place emergency response teams (NDRF/SDRF) on 1-hour standby.",
            "Direct reservoir managers to monitor inflows and prepare controlled discharges.",
            "Issue warnings to coastal fishermen to cease operations.",
            "Conduct checks on critical communication networks and power backups."
        ];
    } else if (riskPercent >= 25) {
        sops = [
            "Monitor district telemetry station data hourly.",
            "Instruct local administrative blocks (Taluks) to inspect flood embankments.",
            "Notify community leaders of potential heavy weather anomalies."
        ];
    } else {
        sops = [
            "Routine meteorological forecast monitoring active.",
            "No emergency actions required."
        ];
    }
    sops.forEach((action, idx) => {
        const li = document.createElement('li');
        li.style.display = 'flex';
        li.style.gap = '8px';
        li.style.alignItems = 'flex-start';
        li.innerHTML = `<input type="checkbox" id="sop-check-${idx}" style="margin-top: 3px; cursor: pointer;"> <label for="sop-check-${idx}" style="cursor: pointer; line-height: 1.3;">${action}</label>`;
        sopList.appendChild(li);
    });

    logConsole(`Selected GIS Node: ${distData.name} (${distData.id}). Risk: ${riskPercent}%`);
}

// Download Situation Report PDF (triggers API or falls back in sandbox)
async function downloadSituationReport() {
    const districtId = state.selectedDistrict;
    if (!districtId) {
        alert("Please select a district first.");
        return;
    }

    const distData = state.districts[districtId];
    const officerName = prompt(`Generate official Situation Report for ${distData.name}.\nEnter officer name:`, "Duty Officer") || "Duty Officer";

    logConsole(`Compiling weather situation report for ${distData.name}...`);

    try {
        const response = await fetch('/api/v1/reports/compile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                district_code: districtId,
                officer_name: officerName
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `SitRep_${distData.name.replace(/\s+/g, '_')}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            logConsole(`Situation Report PDF successfully downloaded for ${distData.name}.`, "success");
        } else {
            throw new Error(`Server returned HTTP ${response.status}`);
        }
    } catch (err) {
        logConsole(`Backend compiling offline or bypassed: ${err.message}`, "info");
        logConsole("Triggering Sandbox Client-side report generation fallback...", "warning");
        triggerMockPdfDownload(distData, officerName);
    }
}

// Sandbox/Offline Local Text SitRep Downloader
function triggerMockPdfDownload(distData, officerName) {
    const popVal = parseInt(distData.population.replace(/,/g, ''), 10) || 0;
    const scaleFactor = Math.min(popVal / 1000000.0, 1.0);
    const hviVal = (distData.riskScore / 100.0) * (0.7 + 0.3 * scaleFactor);

    const reportText = `========================================================================
WEATHER SITUATION REPORT - ${distData.name.toUpperCase()}
========================================================================
Date Generated: ${new Date().toISOString()}
Prepared By: ${officerName}
Status: SANDBOX PILOT DEMO / EMERGENCY USE ONLY

1. Meteorological Forecast Summary
----------------------------------
District: ${distData.name} (${distData.id})
State: ${distData.state}
Population: ${distData.population}
Forecast Rain: ${distData.id === 'district_29' ? '124.8 mm' : '62.0 mm'}
Warning Level: ${distData.id === 'district_29' ? 'RED' : 'AMBER'}

2. Hazard Risk Evaluation
-------------------------
Calculated Flood Risk Score: ${distData.riskScore}%
Human Vulnerability Index (HVI): ${hviVal.toFixed(2)} (scaled by population)
Vulnerability details: ${distData.vulnerability}

3. Recommended NDMA SOP Actions
-------------------------------
${distData.riskScore >= 75 ? 
`[ ] 1. Activate District Emergency Operations Center (DEOC) to 24/7 alert status.
[ ] 2. Initiate immediate evacuation plans for identified low-lying zones.
[ ] 3. Pre-position NDRF and SDRF rescue units.
[ ] 4. Activate emergency shelters and deploy dry food/medical resources.
[ ] 5. Trigger broadcast public warning alerts.` :
`[ ] 1. Place emergency response teams (NDRF/SDRF) on 1-hour standby.
[ ] 2. Direct reservoir managers to monitor inflows and prepare controlled discharges.
[ ] 3. Issue warnings to coastal fishermen to cease operations.
[ ] 4. Conduct checks on critical communication networks and power backups.`
}

Disclaimer: This report was compiled automatically in Sandbox Mode by Project Varun.
========================================================================`;

    const blob = new Blob([reportText], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `SitRep_${distData.name.replace(/\s+/g, '_')}_Sandbox.txt`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    logConsole(`Mock Situation Report compiled and downloaded: SitRep_${distData.name.replace(/\s+/g, '_')}_Sandbox.txt.`, "success");
}

// Preset Prompt Click
function applyPresetPrompt(promptText) {
    const input = document.getElementById('chat-input-field');
    input.value = promptText;
    input.focus();
}

// Chat input Enter key listener
function handleChatKey(event) {
    if (event.key === 'Enter') {
        sendChatMessage();
    }
}

// Send Chat Message
async function sendChatMessage() {
    const input = document.getElementById('chat-input-field');
    const query = input.value.trim();
    if (!query || state.isChatting) return;

    // Append User Message
    appendMessage(query, 'user');
    input.value = '';
    
    // Show Typing Indicator
    state.isChatting = true;
    const typing = document.getElementById('typing-indicator');
    typing.classList.remove('hidden');
    
    // Scroll chat to bottom
    const chatContainer = document.getElementById('chat-messages');
    chatContainer.scrollTop = chatContainer.scrollHeight;

    if (state.mode === 'sandbox') {
        // Sandbox Mock Chat Response
        setTimeout(() => {
            typing.classList.add('hidden');
            state.isChatting = false;
            
            const responseText = getSandboxChatResponse(query);
            appendMessage(responseText, 'bot', true);
        }, 1200);
    } else {
        // Live API Chat Request
        logConsole(`Sending prompt to /api/v1/chat/query...`);
        const langSelect = document.getElementById('chat-lang');
        
        try {
            const response = await fetch('/api/v1/chat/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: query,
                    language: langSelect.value
                })
            });

            typing.classList.add('hidden');
            state.isChatting = false;

            if (response.ok) {
                const data = await response.json();
                // Handle live response structure
                // Standard structure: { response: "text", source_grounding: [...] }
                const messageText = data.response || JSON.stringify(data);
                appendMessage(messageText, 'bot', false, data.source_grounding);
                logConsole("AI assistant query completed successfully.", "success");
            } else {
                const errorData = await response.json().catch(() => ({ detail: "Network Error" }));
                appendMessage(`❌ API Error: ${errorData.detail || 'Could not fetch response from the backend.'}`, 'bot');
                logConsole(`AI query failed: ${errorData.detail || response.statusText}`, "error");
            }
        } catch (err) {
            typing.classList.add('hidden');
            state.isChatting = false;
            appendMessage("❌ Connection Error: Could not connect to the Vercel backend server. Is database configured?", "bot");
            logConsole(`Connection failed to FastAPI /chat/query: ${err.message}`, "error");
        }
    }
}

// Append Chat Message Bubble
function appendMessage(text, sender, isMocked = false, sources = null) {
    const container = document.getElementById('chat-messages');
    const msg = document.createElement('div');
    msg.className = `message ${sender}-message`;
    
    let contentHtml = `<div class="message-content"><p>${text.replace(/\n/g, '<br>')}</p>`;
    
    // Add grounding sources UI if available
    if (sender === 'bot') {
        if (isMocked) {
            contentHtml += `
                <div class="grounding-box">
                    <span class="grounding-source">🛡️ Grounded: Sandbox Graph Nodes (District 29, KR Sagar Reservoir)</span>
                    <span class="grounding-source">📊 Confidence Score: 0.96 (Hallucination Guard Passed)</span>
                </div>
            `;
        } else if (sources && sources.length > 0) {
            contentHtml += `<div class="grounding-box">`;
            sources.forEach(src => {
                contentHtml += `<span class="grounding-source">📍 Source: ${src.node_name || src.id} (${src.type || 'Node'})</span>`;
            });
            contentHtml += `</div>`;
        }
    }
    
    contentHtml += `</div>`;
    
    // Time
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    contentHtml += `<span class="message-time">${time}</span>`;
    
    msg.innerHTML = contentHtml;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
}

// Mock Sandbox Chat responses
function getSandboxChatResponse(query) {
    const q = query.toLowerCase();
    
    if (q.includes('school') || q.includes('mysuru public school')) {
        return "🏫 **Vulnerability Assessment for Mysuru Public School:**\n\n* **Risk Level:** HIGH ALERT (Downstream Overflow)\n* **Trigger:** Krishna Raja Sagara reservoir level is currently at **124.8 ft** (Capacity: 49.45 TMC, near maximum safety spill limits).\n* **Weather Forecast:** Heavy Rain (29°C) in Mysuru with 88% risk score.\n* **Shelter Capacity:** 400 students.\n\n**Recommendation:** Evacuate non-critical classrooms. Prepare to activate the local shelter boundary. Suspend regular classes for the next 24 hours.";
    }
    
    if (q.includes('reservoir') || q.includes('kr sagar') || q.includes('krishna raja')) {
        return "🌊 **Krishna Raja Sagara (KR Sagar) Status:**\n\n* **Current Level:** 124.8 ft / 124.8 ft Max\n* **Current Capacity:** 49.45 TMC\n* **Flow Status:** Spilling into Cauvery River downstream channel.\n* **Threat Level:** Severe flood danger warning issued for downstream assets in Mysuru district.\n\nGrounding verified against local PostGIS network properties.";
    }

    if (q.includes('hospital') || q.includes('bhubaneswar') || q.includes('khordha')) {
        return "🏥 **Bhubaneswar General Hospital Vulnerability Check:**\n\n* **Risk Level:** SAFE / STABLE\n* **Basin Connection:** Mahanadi River Basin.\n* **Capacity:** 500 beds (50 ICU beds).\n* **Forecast:** Thunderstorms (33°C), 62% risk score.\n\n**Recommendation:** Normal operations. Keep standby drainage pumps active in cellars, but no emergency relocation of medical equipment is needed.";
    }

    if (q.includes('alert') || q.includes('odisha') || q.includes('active warnings')) {
        return "⛈️ **Active Weather Alerts:**\n\n1. **Odisha (Khordha/Bhubaneswar):** Amber Alert (Thunderstorms, Wind speed up to 45 km/h, Risk Score: 62).\n2. **Karnataka (Mysuru):** Red Alert / Heavy Rain Alert (Precipitation > 110mm, Risk Score: 88). Severe risk of local reservoir overflow.\n\nAll details parsed from daily IMD Daily Meteorological Bulletins.";
    }
    
    return "I have scanned the Project Varun database nodes. I see two main active district nodes in the pilot area:\n\n1. **Mysuru (Karnataka)**: Currently under a **Red Alert** due to heavy rain. Downstream assets at risk include Mysuru Public School and the Mysuru Power Grid.\n2. **Khordha (Bhubaneswar, Odisha)**: Under an **Amber Alert** for thunderstorms. Local critical infrastructure like Bhubaneswar General Hospital remains stable.\n\nWhat specific asset details or safety thresholds would you like me to pull?";
}

// Ingestion Trigger File Selector
function triggerFileInput() {
    document.getElementById('pdf-file-input').click();
}

// File Selected Handler
function handleFileSelected(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        alert("Only PDF meteorological bulletins are supported.");
        return;
    }

    uploadBulletin(file);
}

// Upload Bulletin
async function uploadBulletin(file) {
    const box = document.getElementById('upload-status-box');
    const title = document.getElementById('upload-status-title');
    const icon = document.getElementById('upload-status-icon');
    const progress = document.getElementById('upload-progress');
    const details = document.getElementById('upload-details-list');

    box.classList.remove('hidden');
    icon.innerText = '🔄';
    title.innerText = `Ingesting ${file.name}...`;
    progress.style.width = '20%';
    details.innerHTML = '<li>Starting multi-tier bulletin parser...</li>';

    logConsole(`Initiated file upload: ${file.name} (Size: ${(file.size / 1024).toFixed(1)} KB)`);

    if (state.mode === 'sandbox') {
        // Sandbox Simulation
        setTimeout(() => {
            progress.style.width = '55%';
            details.innerHTML += '<li>Running layout tiering extraction (Tier 1 PyMuPDF success)...</li>';
            details.innerHTML += '<li>Running Data Quality Service (DQS) validation...</li>';
            logConsole("Parsing layout grids for bulletin...");
        }, 800);

        setTimeout(() => {
            progress.style.width = '100%';
            icon.innerText = '✅';
            title.innerText = 'Ingestion Completed!';
            
            const recId = `rec_sb_${Math.floor(Math.random() * 900000 + 100000)}`;
            details.innerHTML += `<li><strong>DQS Check:</strong> 42 records normalized successfully.</li>`;
            details.innerHTML += `<li><strong>Database Record:</strong> Created standard record ID: <code>${recId}</code></li>`;
            details.innerHTML += `<li><strong>Data Lineage:</strong> Transformation pipeline saved to schema logs.</li>`;
            
            logConsole(`Successfully ingested PDF bulletin in Sandbox. Record ID: ${recId}`, "success");
        }, 1800);
    } else {
        // Production Live upload
        logConsole("Uploading file to /api/v1/ingest/bulletin via Form Data...");
        
        const formData = new FormData();
        formData.append("file", file);

        try {
            progress.style.width = '40%';
            details.innerHTML += '<li>Uploading PDF data package...</li>';
            
            const response = await fetch('/api/v1/ingest/bulletin', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                progress.style.width = '100%';
                icon.innerText = '✅';
                title.innerText = 'Ingestion Successful!';
                
                details.innerHTML += `<li><strong>Parser Tier used:</strong> Tier ${data.tier_used || '1'}</li>`;
                details.innerHTML += `<li><strong>Records Extracted:</strong> ${data.records_parsed} weather payloads</li>`;
                details.innerHTML += `<li><strong>DB Record ID:</strong> <code>${data.record_id}</code></li>`;
                
                logConsole(`Live ingestion completed. Saved record ${data.record_id}`, "success");
            } else {
                const errorData = await response.json().catch(() => ({ detail: "Extraction Failed" }));
                progress.style.width = '100%';
                icon.innerText = '❌';
                title.innerText = 'Ingestion Failed';
                details.innerHTML += `<li style="color: var(--color-danger)"><strong>Error:</strong> ${errorData.detail}</li>`;
                
                logConsole(`Extraction failed on server: ${errorData.detail}`, "error");
            }
        } catch (err) {
            progress.style.width = '100%';
            icon.innerText = '❌';
            title.innerText = 'Network Error';
            details.innerHTML += `<li style="color: var(--color-danger)">Could not connect to FastAPI backend.</li>`;
            logConsole(`Connection failed during upload: ${err.message}`, "error");
        }
    }
}

// Open-Meteo Grid Sync
async function triggerSyncGrid() {
    if (state.isSyncing) return;
    
    state.isSyncing = true;
    const btn = document.getElementById('sync-trigger-button');
    const svgIcon = document.getElementById('sync-icon-svg');
    
    btn.disabled = true;
    svgIcon.classList.add('spinning');
    
    logConsole("Initializing Open-Meteo REST Client...");
    logConsole("Querying weather coordinates centroids for 2 registered district nodes...");

    if (state.mode === 'sandbox') {
        // Sandbox Mock Sync
        setTimeout(() => {
            logConsole("GET requests completed to api.open-meteo.com.", "info");
            logConsole("Received payload sizes: 24.2 KB (Mysuru), 21.8 KB (Khordha).", "info");
            logConsole("Mapping variables: temperature_2m, wind_speed_10m, precipitation_sum.", "info");
        }, 1000);

        setTimeout(() => {
            state.isSyncing = false;
            btn.disabled = false;
            svgIcon.classList.remove('spinning');
            
            state.lastSyncTime = new Date().toLocaleTimeString();
            state.syncedNodesCount = 2;
            
            document.getElementById('last-sync-time').innerText = state.lastSyncTime;
            document.getElementById('synced-nodes-count').innerText = state.syncedNodesCount;
            
            logConsole("DQS Schema validation check: SUCCESS", "success");
            logConsole("Open-Meteo synchronizer finished. 2 records committed to database.", "success");
        }, 2200);
    } else {
        // Production Live Sync
        try {
            logConsole("Sending POST request to /api/v1/ingest/sync-grid...");
            const response = await fetch('/api/v1/ingest/sync-grid', {
                method: 'POST'
            });

            state.isSyncing = false;
            btn.disabled = false;
            svgIcon.classList.remove('spinning');

            if (response.ok) {
                const data = await response.json();
                
                state.lastSyncTime = new Date().toLocaleTimeString();
                state.syncedNodesCount = data.districts_synced || 0;
                
                document.getElementById('last-sync-time').innerText = state.lastSyncTime;
                document.getElementById('synced-nodes-count').innerText = state.syncedNodesCount;
                
                logConsole(`Live synchronizer successfully completed. Nodes synced: ${data.districts_synced}`, "success");
            } else {
                const errorData = await response.json().catch(() => ({ detail: "Sync task failed" }));
                logConsole(`Live sync task failed: ${errorData.detail || response.statusText}`, "error");
            }
        } catch (err) {
            state.isSyncing = false;
            btn.disabled = false;
            svgIcon.classList.remove('spinning');
            logConsole(`Live sync request failed: ${err.message}`, "error");
        }
    }
}
