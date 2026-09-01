// Industrial PPE Compliance AI - Live Dashboard Controller

let trendChart = null;
let ppeChart = null;

document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    connectWebSocket();
    loadIncidents();
});

// Initialize Chart.js
function initCharts() {
    const ctxTrend = document.getElementById("trendChart").getContext("2d");
    trendChart = new Chart(ctxTrend, {
        type: "line",
        data: {
            labels: ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00"],
            datasets: [{
                label: "Violations per Hour",
                data: [0, 0, 0, 0, 0, 0],
                borderColor: "#ef4444",
                backgroundColor: "rgba(239, 68, 68, 0.15)",
                fill: true,
                tension: 0.4,
                borderWidth: 2,
                pointBackgroundColor: "#ef4444"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: "rgba(255, 255, 255, 0.05)" }, ticks: { color: "#94a3b8" } },
                y: { grid: { color: "rgba(255, 255, 255, 0.05)" }, ticks: { color: "#94a3b8", stepSize: 1 }, beginAtZero: true }
            }
        }
    });

    const ctxPpe = document.getElementById("ppeBreakdownChart").getContext("2d");
    ppeChart = new Chart(ctxPpe, {
        type: "doughnut",
        data: {
            labels: ["Missing Helmet", "Missing Safety Vest", "Missing Boots"],
            datasets: [{
                data: [1, 1, 0],
                backgroundColor: ["#ef4444", "#f59e0b", "#8b5cf6"],
                borderColor: "#0a0d14",
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "bottom", labels: { color: "#94a3b8", boxWidth: 12 } }
            }
        }
    });
}

// Connect Real-Time WebSocket Telemetry
function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;
    const socket = new WebSocket(wsUrl);

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateTelemetry(data.kpis);
        if (data.recent_incidents) {
            renderIncidents(data.recent_incidents);
        }
    };

    socket.onclose = () => {
        setTimeout(connectWebSocket, 3000);
    };
}

function updateTelemetry(kpis) {
    if (!kpis) return;

    document.getElementById("valCompliance").innerText = `${kpis.compliance_rate_percent}%`;
    document.getElementById("valActiveWorkers").innerText = kpis.active_workers_count;
    document.getElementById("valTotalViolations").innerText = kpis.total_violations_today;

    // Update Trend Chart
    if (kpis.hourly_trend && trendChart) {
        const labels = Object.keys(kpis.hourly_trend);
        const values = Object.values(kpis.hourly_trend);
        trendChart.data.labels = labels;
        trendChart.data.datasets[0].data = values;
        trendChart.update();
    }

    // Update PPE Breakdown
    if (kpis.ppe_breakdown && ppeChart) {
        const labels = Object.keys(kpis.ppe_breakdown);
        const values = Object.values(kpis.ppe_breakdown);
        ppeChart.data.labels = labels;
        ppeChart.data.datasets[0].data = values;
        ppeChart.update();
    }
}

// Fetch and Render Incident Table
async function loadIncidents() {
    try {
        const res = await fetch("/api/incidents?limit=10");
        const incidents = await res.json();
        renderIncidents(incidents);
    } catch (e) {
        console.error("Failed loading incidents:", e);
    }
}

function renderIncidents(incidents) {
    const tbody = document.getElementById("incidentTableBody");
    if (!tbody || !incidents) return;

    if (incidents.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #94a3b8; padding: 20px;">No safety violations recorded today. All personnel compliant.</td></tr>`;
        return;
    }

    tbody.innerHTML = incidents.map(inc => {
        let snapUrl = "";
        if (inc.snapshot_path) {
            snapUrl = inc.snapshot_path.startsWith('/') ? inc.snapshot_path : (inc.snapshot_path.startsWith('snapshots/') ? '/' + inc.snapshot_path : '/snapshots/' + inc.snapshot_path);
        }
        return `
        <tr>
            <td><strong>#${inc.id}</strong></td>
            <td>${inc.timestamp}</td>
            <td>${inc.zone_name}</td>
            <td>Worker #${inc.worker_track_id}</td>
            <td><span class="badge ${inc.status === 'UNRESOLVED' ? 'badge-danger' : 'badge-success'}">${inc.violation_type}</span></td>
            <td>
                ${snapUrl ? `<img src="${snapUrl}" class="snapshot-thumb" alt="Evidence" onclick="window.open('${snapUrl}', '_blank')" />` : '<span style="color:#64748b">No Snap</span>'}
            </td>
            <td>
                ${inc.status === 'UNRESOLVED' ? `<button class="btn-resolve" onclick="resolveIncident(${inc.id})">Resolve</button>` : '<span style="color:#10b981; font-weight:600">✓ Resolved</span>'}
            </td>
        </tr>
    `}).join("");
}

async function resolveIncident(id) {
    try {
        await fetch(`/api/incidents/${id}/resolve`, { method: "POST" });
        loadIncidents();
    } catch (e) {
        console.error("Failed resolving incident:", e);
    }
}
