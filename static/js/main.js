// ─── BRIGHTHAVEN MAIN.JS ───────────────────────────────────────────────────

// ─── SIDEBAR ───────────────────────────────────────────────────────────────
function initSidebar() {
    const toggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    if (!toggle || !sidebar) return;

    toggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
        if (overlay) overlay.classList.toggle('open');
    });
    if (overlay) {
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.classList.remove('open');
        });
    }

    // Highlight active link
    const currentPath = window.location.pathname;
    document.querySelectorAll('.sidebar-link').forEach(link => {
        if (link.href && link.href.includes(currentPath) && currentPath !== '/') {
            link.classList.add('active');
        }
    });
}

// ─── CLOCK ──────────────────────────────────────────────────────────────────
function initClock() {
    const el = document.getElementById('liveClock');
    if (!el) return;
    function update() {
        const now = new Date();
        el.textContent = now.toLocaleString('en-IN', {
            weekday:'short', year:'numeric', month:'short',
            day:'numeric', hour:'2-digit', minute:'2-digit', second:'2-digit'
        });
    }
    update();
    setInterval(update, 1000);
}

// ─── DEVICE TOGGLE ──────────────────────────────────────────────────────────
function toggleDevice(deviceId, state, callback) {
    fetch('/user/api/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device: deviceId, state: state })
    })
    .then(r => r.json())
    .then(data => {
        if (callback) callback(data.ok);
        if (!data.ok) showToast('Failed to toggle device', 'error');
    })
    .catch(() => showToast('Connection error', 'error'));
}

function toggleRoom(room, state, callback) {
    fetch('/user/api/toggle-room', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room: room, state: state })
    })
    .then(r => r.json())
    .then(data => { if (callback) callback(data.ok); })
    .catch(() => showToast('Connection error', 'error'));
}

function toggleAll(state, callback) {
    fetch('/user/api/toggle-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: state })
    })
    .then(r => r.json())
    .then(data => { if (callback) callback(data.ok); })
    .catch(() => showToast('Connection error', 'error'));
}

// ─── STATUS POLLING ──────────────────────────────────────────────────────────
function pollDeviceStatus(interval = 5000) {
    function fetch_status() {
        fetch('/user/api/status')
            .then(r => r.json())
            .then(data => {
                Object.entries(data).forEach(([devId, isOn]) => {
                    // Update toggle switches
                    const toggle = document.querySelector(`[data-device="${devId}"]`);
                    if (toggle) {
                        toggle.checked = isOn;
                        updateDeviceCard(devId, isOn);
                    }
                    // Update status text
                    const statusEl = document.getElementById(`status_${devId}`);
                    if (statusEl) {
                        statusEl.textContent = isOn ? 'ON' : 'OFF';
                        statusEl.className = isOn ? 'badge badge-on' : 'badge badge-off';
                    }
                });
            })
            .catch(() => {}); // Silent fail for polling
    }
    fetch_status();
    return setInterval(fetch_status, interval);
}

function updateDeviceCard(devId, isOn) {
    const card = document.querySelector(`.device-card[data-device-id="${devId}"]`);
    if (!card) return;
    if (isOn) {
        card.classList.add('device-on');
    } else {
        card.classList.remove('device-on');
    }
}

// ─── TOAST NOTIFICATIONS ────────────────────────────────────────────────────
function showToast(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.cssText = `
            position: fixed; bottom: 24px; right: 24px;
            display: flex; flex-direction: column; gap: 8px;
            z-index: 9999; pointer-events: none;
        `;
        document.body.appendChild(container);
    }

    const colors = {
        success: 'rgba(39,174,96,0.95)',
        error:   'rgba(192,57,43,0.95)',
        warning: 'rgba(212,175,55,0.95)',
        info:    'rgba(52,152,219,0.95)'
    };

    const toast = document.createElement('div');
    toast.style.cssText = `
        background: ${colors[type] || colors.info};
        color: #fff; padding: 12px 20px; border-radius: 10px;
        font-size: 0.875rem; font-weight: 500;
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        animation: slideInRight 0.3s ease, fadeOut 0.3s ease 2.7s forwards;
        pointer-events: auto; max-width: 280px;
        font-family: 'DM Sans', sans-serif;
    `;
    toast.textContent = message;

    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to   { transform: translateX(0); opacity: 1; }
        }
        @keyframes fadeOut {
            to { opacity: 0; transform: translateX(100%); }
        }
    `;
    if (!document.getElementById('toastStyles')) {
        style.id = 'toastStyles';
        document.head.appendChild(style);
    }

    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// ─── LOADER ──────────────────────────────────────────────────────────────────
function initLoader() {
    const loader = document.getElementById('logo-loader');
    if (!loader) return;
    // Only show on first load per session
    if (sessionStorage.getItem('bh_loaded')) {
        loader.classList.add('hidden');
        return;
    }
    sessionStorage.setItem('bh_loaded', '1');
    setTimeout(() => loader.classList.add('hidden'), 3000);
}

// ─── CONFIRM DELETE ──────────────────────────────────────────────────────────
function confirmDelete(formEl) {
    if (confirm('Are you sure? This action cannot be undone.')) {
        formEl.submit();
    }
}

// ─── AUTO-DISMISS ALERTS ─────────────────────────────────────────────────────
function initAlerts() {
    document.querySelectorAll('.alert[data-auto-dismiss]').forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s';
            setTimeout(() => alert.remove(), 500);
        }, 4000);
    });
}

// ─── INIT ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    initClock();
    initLoader();
    initAlerts();
});
