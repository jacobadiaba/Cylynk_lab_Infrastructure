/**
 * CyberLab AttackBox Launcher - Test Application
 * Simulates Moodle integration with the Orchestrator API
 */

// State
let currentSession = null;
let pollInterval = null;

// DOM Elements
const elements = {
    apiEndpoint: document.getElementById('apiEndpoint'),
    apiKey: document.getElementById('apiKey'),
    studentId: document.getElementById('studentId'),
    studentName: document.getElementById('studentName'),
    courseId: document.getElementById('courseId'),
    labId: document.getElementById('labId'),
    launchBtn: document.getElementById('launchBtn'),
    statusBtn: document.getElementById('statusBtn'),
    terminateBtn: document.getElementById('terminateBtn'),
    sessionPanel: document.getElementById('sessionPanel'),
    sessionInfo: document.getElementById('sessionInfo'),
    connectionPanel: document.getElementById('connectionPanel'),
    guacamoleLink: document.getElementById('guacamoleLink'),
    instanceIp: document.getElementById('instanceIp'),
    logsContainer: document.getElementById('logsContainer'),
    clearLogs: document.getElementById('clearLogs'),
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Load saved config from localStorage
    loadConfig();
    
    // Event listeners
    elements.launchBtn.addEventListener('click', launchAttackBox);
    elements.statusBtn.addEventListener('click', checkStatus);
    elements.terminateBtn.addEventListener('click', terminateSession);
    elements.clearLogs.addEventListener('click', clearLogs);
    
    // Save config on change
    ['apiEndpoint', 'apiKey', 'studentId', 'studentName', 'courseId', 'labId'].forEach(id => {
        elements[id].addEventListener('change', saveConfig);
    });
    
    log('info', 'Test app initialized. Configure your API endpoint and click "Launch AttackBox".');
});

// Config Management
function loadConfig() {
    const config = JSON.parse(localStorage.getItem('cyberlabConfig') || '{}');
    if (config.apiEndpoint) elements.apiEndpoint.value = config.apiEndpoint;
    if (config.apiKey) elements.apiKey.value = config.apiKey;
    if (config.studentId) elements.studentId.value = config.studentId;
    if (config.studentName) elements.studentName.value = config.studentName;
    if (config.courseId) elements.courseId.value = config.courseId;
    if (config.labId) elements.labId.value = config.labId;
    
    // Load saved session
    const savedSession = JSON.parse(localStorage.getItem('cyberlabSession') || 'null');
    if (savedSession) {
        currentSession = savedSession;
        updateSessionUI();
    }
}

function saveConfig() {
    const config = {
        apiEndpoint: elements.apiEndpoint.value,
        apiKey: elements.apiKey.value,
        studentId: elements.studentId.value,
        studentName: elements.studentName.value,
        courseId: elements.courseId.value,
        labId: elements.labId.value,
    };
    localStorage.setItem('cyberlabConfig', JSON.stringify(config));
}

function saveSession() {
    localStorage.setItem('cyberlabSession', JSON.stringify(currentSession));
}

// API Helpers
function getApiUrl(path) {
    const base = elements.apiEndpoint.value.replace(/\/$/, '');
    return `${base}${path}`;
}

function getHeaders() {
    const headers = {
        'Content-Type': 'application/json',
    };
    if (elements.apiKey.value) {
        headers['X-Api-Key'] = elements.apiKey.value;
    }
    return headers;
}

async function apiRequest(method, path, body = null) {
    const url = getApiUrl(path);
    
    log('request', `${method} ${url}`);
    if (body) {
        log('request', `Body: ${JSON.stringify(body, null, 2)}`);
    }
    
    try {
        const options = {
            method,
            headers: getHeaders(),
            mode: 'cors',
        };
        
        if (body) {
            options.body = JSON.stringify(body);
        }
        
        const response = await fetch(url, options);
        const data = await response.json();
        
        if (response.ok) {
            log('response', `Status: ${response.status}`);
            log('response', `Response: ${JSON.stringify(data, null, 2)}`);
        } else {
            log('error', `Status: ${response.status}`);
            log('error', `Error: ${JSON.stringify(data, null, 2)}`);
        }
        
        return { ok: response.ok, status: response.status, data };
    } catch (error) {
        log('error', `Network error: ${error.message}`);
        return { ok: false, error: error.message };
    }
}

// Actions
async function launchAttackBox() {
    if (!validateConfig()) return;
    
    setButtonLoading(elements.launchBtn, true);
    
    const body = {
        student_id: elements.studentId.value,
        student_name: elements.studentName.value,
        course_id: elements.courseId.value,
        lab_id: elements.labId.value,
        metadata: {
            source: 'test-app',
            timestamp: new Date().toISOString(),
        },
    };
    
    const result = await apiRequest('POST', '/sessions', body);
    
    setButtonLoading(elements.launchBtn, false);
    
    if (result.ok && result.data.success) {
        currentSession = result.data.data;
        saveSession();
        updateSessionUI();
        
        // Start polling if provisioning
        if (currentSession.status === 'provisioning' || currentSession.status === 'pending') {
            startPolling();
        }
    } else {
        showError(result.data?.error || result.error || 'Failed to launch AttackBox');
    }
}

async function checkStatus() {
    if (!currentSession?.session_id) {
        log('info', 'No active session to check');
        return;
    }
    
    setButtonLoading(elements.statusBtn, true);
    
    const result = await apiRequest('GET', `/sessions/${currentSession.session_id}`);
    
    setButtonLoading(elements.statusBtn, false);
    
    if (result.ok && result.data.success) {
        currentSession = result.data.data;
        saveSession();
        updateSessionUI();
    } else {
        showError(result.data?.error || result.error || 'Failed to get status');
    }
}

async function terminateSession() {
    if (!currentSession?.session_id) {
        log('info', 'No active session to terminate');
        return;
    }
    
    if (!confirm('Are you sure you want to terminate this session?')) {
        return;
    }
    
    setButtonLoading(elements.terminateBtn, true);
    stopPolling();
    
    const result = await apiRequest('DELETE', `/sessions/${currentSession.session_id}`);
    
    setButtonLoading(elements.terminateBtn, false);
    
    if (result.ok && result.data.success) {
        currentSession = result.data.data;
        saveSession();
        updateSessionUI();
        log('info', 'Session terminated successfully');
    } else {
        showError(result.data?.error || result.error || 'Failed to terminate session');
    }
}

// Polling
function startPolling() {
    if (pollInterval) return;
    
    log('info', 'Starting status polling (every 10 seconds)...');
    
    pollInterval = setInterval(async () => {
        if (!currentSession?.session_id) {
            stopPolling();
            return;
        }
        
        const result = await apiRequest('GET', `/sessions/${currentSession.session_id}`);
        
        if (result.ok && result.data.success) {
            currentSession = result.data.data;
            saveSession();
            updateSessionUI();
            
            // Stop polling when ready or terminated
            if (['ready', 'active', 'terminated', 'error'].includes(currentSession.status)) {
                stopPolling();
                if (currentSession.status === 'ready' || currentSession.status === 'active') {
                    log('info', '🎉 AttackBox is ready! Click the Guacamole link to connect.');
                }
            }
        }
    }, 10000);
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
        log('info', 'Stopped status polling');
    }
}

// UI Updates
function updateSessionUI() {
    if (!currentSession) {
        elements.sessionInfo.innerHTML = '<div class="no-session">No active session. Click "Launch AttackBox" to start.</div>';
        elements.connectionPanel.classList.add('hidden');
        return;
    }
    
    const statusClass = `status-${currentSession.status}`;
    const statusIcon = getStatusIcon(currentSession.status);
    
    let expiresAt = '-';
    if (currentSession.expires_at) {
        const expDate = new Date(currentSession.expires_at * 1000);
        expiresAt = expDate.toLocaleString();
    }
    
    let createdAt = '-';
    if (currentSession.created_at) {
        const createDate = new Date(currentSession.created_at * 1000);
        createdAt = createDate.toLocaleString();
    }
    
    elements.sessionInfo.innerHTML = `
        <div class="session-card">
            <div class="session-row">
                <span class="session-label">Session ID</span>
                <span class="session-value">${currentSession.session_id || '-'}</span>
            </div>
            <div class="session-row">
                <span class="session-label">Status</span>
                <span class="session-value">
                    <span class="status-badge ${statusClass}">${statusIcon} ${currentSession.status || '-'}</span>
                </span>
            </div>
            <div class="session-row">
                <span class="session-label">Instance ID</span>
                <span class="session-value">${currentSession.instance_id || '-'}</span>
            </div>
            <div class="session-row">
                <span class="session-label">Instance IP</span>
                <span class="session-value">${currentSession.instance_ip || '-'}</span>
            </div>
            <div class="session-row">
                <span class="session-label">Created</span>
                <span class="session-value">${createdAt}</span>
            </div>
            <div class="session-row">
                <span class="session-label">Expires</span>
                <span class="session-value">${expiresAt}</span>
            </div>
            ${currentSession.error ? `
            <div class="session-row">
                <span class="session-label">Error</span>
                <span class="session-value" style="color: var(--accent-red)">${currentSession.error}</span>
            </div>
            ` : ''}
        </div>
    `;
    
    // Show connection panel if ready
    if ((currentSession.status === 'ready' || currentSession.status === 'active') && currentSession.connection_info) {
        elements.connectionPanel.classList.remove('hidden');
        
        const connInfo = currentSession.connection_info;
        
        // Use direct RDP connection URL if available, otherwise fall back to base Guacamole URL
        const connectionUrl = connInfo.direct_url || connInfo.guacamole_connection_url || connInfo.guacamole_url || '#';
        elements.guacamoleLink.href = connectionUrl;
        elements.instanceIp.textContent = connInfo.instance_ip || currentSession.instance_ip || '-';
        
        // Log connection details
        if (connInfo.guacamole_connection_id) {
            log('info', `Guacamole connection created: ${connInfo.guacamole_connection_id}`);
        }
        if (connInfo.direct_url) {
            log('info', `Direct RDP URL ready - click "Open Guacamole" to connect`);
        }
    } else {
        elements.connectionPanel.classList.add('hidden');
    }
}

function getStatusIcon(status) {
    const icons = {
        pending: '⏳',
        provisioning: '🔄',
        ready: '✅',
        active: '🟢',
        terminating: '⏹️',
        terminated: '🔴',
        error: '❌',
    };
    return icons[status] || '❓';
}

// Logging
function log(type, message) {
    const timestamp = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;
    entry.innerHTML = `<span class="log-timestamp">[${timestamp}]</span>${escapeHtml(message)}`;
    
    elements.logsContainer.appendChild(entry);
    elements.logsContainer.scrollTop = elements.logsContainer.scrollHeight;
}

function clearLogs() {
    elements.logsContainer.innerHTML = '<div class="log-entry log-info">Logs cleared.</div>';
}

// Helpers
function validateConfig() {
    if (!elements.apiEndpoint.value) {
        showError('Please enter the API endpoint');
        elements.apiEndpoint.focus();
        return false;
    }
    if (!elements.studentId.value) {
        showError('Please enter a Student ID');
        elements.studentId.focus();
        return false;
    }
    return true;
}

function showError(message) {
    log('error', message);
    alert(message);
}

function setButtonLoading(button, loading) {
    button.disabled = loading;
    if (loading) {
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = '<span class="btn-icon">⏳</span> Loading...';
    } else if (button.dataset.originalText) {
        button.innerHTML = button.dataset.originalText;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stopPolling();
});

