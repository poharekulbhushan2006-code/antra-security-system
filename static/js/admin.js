/**
 * AegisVault Admin & Evidence Management Controller
 */

let enrollDescriptor = null;
let enrollPhotoBase64 = null;
let enrollStream = null;
let modelsReady = false;

// DOM references
const enrollVideo = document.getElementById('enrollVideo');
const enrollCanvas = document.getElementById('enrollCanvas');
const enrollStatus = document.getElementById('enrollFaceStatus');

async function initAdmin() {
    checkAdminGate();
    // Load models
    try {
        await faceapi.nets.tinyFaceDetector.loadFromUri('/static/models');
        await faceapi.nets.faceLandmark68Net.loadFromUri('/static/models');
        await faceapi.nets.faceRecognitionNet.loadFromUri('/static/models');
        modelsReady = true;
        console.log("Admin models loaded.");
    } catch (e) {
        console.error("Failed to load models in admin:", e);
    }

    loadIntruders();
    loadUsers();
    loadAuditLogs();
    loadSettings();
}

// --- Navigation Tabs ---

function switchTab(tabId) {
    ['intruders', 'enrollment', 'audit', 'settings'].forEach(id => {
        const sec = document.getElementById(`tab-${id}`);
        const btn = document.getElementById(`tabBtn-${id}`);
        if (id === tabId) {
            sec.style.display = 'grid';
            btn.classList.add('active');
        } else {
            sec.style.display = 'none';
            btn.classList.remove('active');
        }
    });

    if (tabId === 'enrollment' && !enrollStream) {
        startEnrollCamera();
    }
}

// --- Personnel Enrollment & Face Capture ---

async function startEnrollCamera() {
    try {
        if (enrollStream) {
            enrollStream.getTracks().forEach(t => t.stop());
        }
        enrollStream = await navigator.mediaDevices.getUserMedia({
            video: { width: 480, height: 360, facingMode: 'user' },
            audio: false
        });
        enrollVideo.srcObject = enrollStream;
        enrollVideo.onloadedmetadata = () => {
            enrollVideo.play();
            enrollCanvas.width = enrollVideo.videoWidth || 480;
            enrollCanvas.height = enrollVideo.videoHeight || 360;
        };
        enrollStatus.textContent = "Camera active. Position face directly in frame, then click 'Scan & Lock Face ID'.";
        enrollStatus.style.color = "var(--accent-cyan)";
    } catch (err) {
        enrollStatus.textContent = "Camera error: " + err.message;
        enrollStatus.style.color = "var(--accent-crimson)";
    }
}

async function captureEnrollDescriptor() {
    if (!modelsReady) {
        alert("Neural models are still initializing. Please wait a moment.");
        return;
    }
    enrollStatus.textContent = "Analyzing facial geometry and computing 128-d embedding...";
    enrollStatus.style.color = "var(--accent-cyan)";

    try {
        const detection = await faceapi
            .detectSingleFace(enrollVideo, new faceapi.TinyFaceDetectorOptions({ inputSize: 320, scoreThreshold: 0.5 }))
            .withFaceLandmarks()
            .withFaceDescriptor();

        if (!detection) {
            enrollStatus.textContent = "❌ No face detected. Look directly at the camera and ensure good lighting.";
            enrollStatus.style.color = "var(--accent-crimson)";
            return;
        }

        // Draw bounding box on enroll canvas
        const ctx = enrollCanvas.getContext('2d');
        ctx.clearRect(0, 0, enrollCanvas.width, enrollCanvas.height);
        const { x, y, width, height } = detection.detection.box;
        ctx.strokeStyle = '#10b981';
        ctx.lineWidth = 3;
        ctx.strokeRect(x, y, width, height);

        // Save descriptor & snapshot
        enrollDescriptor = Array.from(detection.descriptor);

        // Capture photo snapshot
        const snap = document.createElement('canvas');
        snap.width = enrollVideo.videoWidth;
        snap.height = enrollVideo.videoHeight;
        const snapCtx = snap.getContext('2d');
        snapCtx.translate(snap.width, 0);
        snapCtx.scale(-1, 1);
        snapCtx.drawImage(enrollVideo, 0, 0);
        enrollPhotoBase64 = snap.toDataURL('image/jpeg', 0.9);

        enrollStatus.textContent = "✅ Biometric signature locked! 128-d descriptor extracted successfully.";
        enrollStatus.style.color = "var(--accent-emerald)";
    } catch (err) {
        console.error("Enroll capture error:", err);
        enrollStatus.textContent = "Detection error: " + err.message;
        enrollStatus.style.color = "var(--accent-crimson)";
    }
}

async function handleEnrollSubmit(e) {
    e.preventDefault();
    if (!enrollDescriptor) {
        alert("Please capture the personnel's face by clicking 'Scan & Lock Face ID' first.");
        return;
    }

    const name = document.getElementById('regName').value;
    const employeeId = document.getElementById('regEmpId').value;
    const role = document.getElementById('regRole').value;
    const pin = document.getElementById('regPin').value;

    const btn = document.getElementById('btnSubmitEnroll');
    btn.disabled = true;
    btn.textContent = "ENROLLING...";

    try {
        const res = await fetch('/api/register-user', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                employee_id: employeeId,
                role: role,
                pin: pin,
                descriptor: enrollDescriptor,
                image_base64: enrollPhotoBase64
            })
        });

        const data = await res.json();
        if (res.ok && data.success) {
            alert(`Authorized Personnel '${name}' successfully enrolled!`);
            document.getElementById('enrollForm').reset();
            enrollDescriptor = null;
            enrollPhotoBase64 = null;
            enrollStatus.textContent = "Personnel enrolled. Ready for next registration.";
            const ctx = enrollCanvas.getContext('2d');
            ctx.clearRect(0, 0, enrollCanvas.width, enrollCanvas.height);
            loadUsers();
            loadAuditLogs();
        } else {
            alert("Enrollment failed: " + (data.detail || data.message || "Unknown error"));
        }
    } catch (err) {
        alert("Enrollment error: " + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "REGISTER & ENROLL PERSONNEL";
    }
}

// --- Active Directory & Revocation ---

async function loadUsers() {
    try {
        const res = await fetch('/api/users');
        const data = await res.json();
        const users = data.users || [];
        document.getElementById('userCount').textContent = users.length;

        const container = document.getElementById('userDirectory');
        if (users.length === 0) {
            container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 2rem; text-align: center;">No authorized personnel currently enrolled. Use the form to enroll your first user.</div>`;
            return;
        }

        container.innerHTML = users.map(u => `
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.9rem 1rem; border-bottom: 1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.02); margin-bottom: 6px; border-radius: 8px;">
                <div style="display: flex; align-items: center; gap: 0.9rem;">
                    <div style="width: 44px; height: 44px; border-radius: 50%; overflow: hidden; background: #1e293b; border: 2px solid var(--accent-cyan); display: flex; align-items: center; justify-content: center;">
                        ${u.photo_filename ? `<img src="/evidence/users/${u.photo_filename}" style="width: 100%; height: 100%; object-fit: cover;">` : `<span style="font-size: 20px;">👤</span>`}
                    </div>
                    <div>
                        <div style="font-weight: 700; font-size: 0.92rem; color: #fff;">${u.name}</div>
                        <div style="font-size: 0.75rem; color: var(--accent-cyan); font-family: var(--font-mono);">${u.employee_id} &bull; ${u.role}</div>
                        <div style="font-size: 0.68rem; color: var(--text-muted);">Enrolled: ${new Date(u.created_at).toLocaleString()}</div>
                    </div>
                </div>
                <div>
                    <button onclick="revokeUser(${u.id}, '${u.name}')" class="nav-btn" style="font-size: 0.75rem; border-color: rgba(239,68,68,0.4); color: #f87171;">
                        Revoke
                    </button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error("Failed to load users:", e);
    }
}

async function revokeUser(userId, name) {
    if (!confirm(`Are you sure you want to revoke vault access for ${name}?`)) return;

    try {
        const res = await fetch(`/api/users/${userId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            loadUsers();
            loadAuditLogs();
        } else {
            alert(data.detail || "Failed to revoke user");
        }
    } catch (e) {
        alert("Error: " + e.message);
    }
}

// --- Intruder Evidence Gallery ---

function getWhatsAppDispatchUrl(item) {
    const origin = window.location.origin;
    const photoUrl = `${origin}/evidence/intruders/${item.photo_filename}`;
    const rawPhone = (window.adminPhoneNumber || document.getElementById('setAdminPhone')?.value || '9834481366').replace(/\D/g, '');
    const waPhone = rawPhone.startsWith('91') && rawPhone.length === 12 ? rawPhone : (rawPhone.length === 10 ? '91' + rawPhone : rawPhone);
    const waText = encodeURIComponent(`🚨 ANTRA SECURITY ALERT: Unregistered person intercepted at Vault Entrance!\nIncident #${item.id} on ${new Date(item.timestamp).toLocaleString()}.\nThreat Level: ${item.threat_level}\nView Photo: ${photoUrl}`);
    return `https://api.whatsapp.com/send?phone=${waPhone}&text=${waText}`;
}

async function loadIntruders() {
    try {
        const res = await fetch('/api/intruders');
        const data = await res.json();
        const list = data.intruders || [];
        const countEl = document.getElementById('intruderCount');
        if (countEl) countEl.textContent = list.length;

        const badge = document.getElementById('intruderBadge');
        const unresolved = list.filter(i => !i.resolved).length;
        if (badge) {
            badge.textContent = `${unresolved} Alerts`;
            badge.style.display = unresolved > 0 ? 'inline-block' : 'none';
        }

        const container = document.getElementById('intruderGallery');
        if (list.length === 0) {
            container.innerHTML = `<div style="grid-column: span 3; color: var(--text-muted); font-size: 0.85rem; padding: 3rem; text-align: center;">✅ No intrusion incidents recorded yet. All secure.</div>`;
            return;
        }

        container.innerHTML = list.map(item => {
            let emailBadge = '<span style="color: #64748b; font-size: 0.65rem;">Email: Unsent</span>';
            if (item.email_sent === 1) emailBadge = '<span style="color: #34d399; font-size: 0.65rem; font-weight: bold;">📧 Email Sent</span>';
            else if (item.email_sent === 2) emailBadge = '<span style="color: #fbbf24; font-size: 0.65rem;">📧 Logged (Simulated)</span>';
            else if (item.email_sent === -1) emailBadge = '<span style="color: #f87171; font-size: 0.65rem;">📧 Email Failed</span>';

            const waUrl = getWhatsAppDispatchUrl(item);

            return `
                <div class="intruder-card" onclick='openEvidenceModal(${JSON.stringify(item)})'>
                    <img src="/evidence/intruders/${item.photo_filename}" alt="Intruder Photo" onerror="this.src='/static/favicon.png'">
                    <div class="intruder-card-body">
                        <div class="intruder-time">${new Date(item.timestamp).toLocaleString()}</div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                            <span class="intruder-badge">${item.threat_level}</span>
                            ${item.resolved ? '<span style="color: #34d399; font-size: 0.7rem; font-weight: bold;">✓ Resolved</span>' : '<span style="color: #f87171; font-size: 0.7rem; font-weight: bold;">⚠️ Pending</span>'}
                        </div>
                        <div style="margin-top: 4px;">${emailBadge}</div>
                        <div style="margin-top: 6px;">
                            <a href="${waUrl}" target="_blank" onclick="event.stopPropagation()" class="nav-btn" style="padding: 0.25rem 0.55rem; font-size: 0.68rem; background: #25D366; color: #fff; border: none; text-decoration: none; display: inline-flex; align-items: center; gap: 4px;">
                                💬 WhatsApp Alert
                            </a>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error("Failed to load intruders:", e);
    }
}

function openEvidenceModal(item) {
    const modal = document.getElementById('evidenceModal');
    const img = document.getElementById('modalImg');
    const details = document.getElementById('modalDetails');
    const resolveBtn = document.getElementById('modalResolveBtn');

    const origin = window.location.origin;
    const photoUrl = `${origin}/evidence/intruders/${item.photo_filename}`;
    const waUrl = getWhatsAppDispatchUrl(item);
    const targetPhone = window.adminPhoneNumber || '9834481366';
    const targetEmail = window.adminAlertEmail || 'poharekulbhushan2006@gmail.com';

    img.src = `/evidence/intruders/${item.photo_filename}`;
    details.innerHTML = `
        <div><strong>Incident ID:</strong> #${item.id}</div>
        <div><strong>Timestamp:</strong> ${new Date(item.timestamp).toLocaleString()}</div>
        <div><strong>Detection Reason:</strong> ${item.reason}</div>
        <div><strong>Threat Assessment:</strong> <span class="badge-critical">${item.threat_level}</span></div>
        <div><strong>Notification Dispatched:</strong> ${item.email_recipient ? item.email_recipient : targetEmail}</div>
        <div><strong>Phone Broadcast:</strong> +91 ${targetPhone} (Direct WhatsApp & SMS)</div>
        <div><strong>Status:</strong> ${item.resolved ? '<span style="color:#34d399;">Resolved & Archived</span>' : '<span style="color:#ef4444;">Active Incident Investigation</span>'}</div>
        <div style="margin-top: 14px; display: flex; gap: 8px; flex-wrap: wrap;">
            <a href="${waUrl}" target="_blank" class="nav-btn" style="background: #25D366; color: #fff; border-color: #22c55e; font-size: 0.8rem; text-decoration: none;">
                📲 Dispatch Photo via WhatsApp (+91 ${targetPhone})
            </a>
            <a href="${photoUrl}" target="_blank" class="nav-btn" style="font-size: 0.8rem; text-decoration: none;">
                🔍 View Full Res Photo
            </a>
        </div>
    `;

    resolveBtn.onclick = async () => {
        await resolveIntruderIncident(item.id);
        closeEvidenceModal();
    };

    modal.style.display = 'flex';
}

function closeEvidenceModal() {
    document.getElementById('evidenceModal').style.display = 'none';
}

async function resolveIntruderIncident(id) {
    try {
        const res = await fetch(`/api/intruders/${id}/resolve`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            loadIntruders();
            loadAuditLogs();
        }
    } catch (e) {
        alert("Failed to resolve incident: " + e.message);
    }
}

// --- Security Audit Logs ---

async function loadAuditLogs() {
    try {
        const res = await fetch('/api/audit-logs');
        const data = await res.json();
        const logs = data.logs || [];
        const tbody = document.getElementById('auditTableBody');

        if (logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No audit entries.</td></tr>`;
            return;
        }

        tbody.innerHTML = logs.map(l => {
            let statusBadge = `<span class="badge-success">${l.status}</span>`;
            if (l.status === 'WARNING') statusBadge = `<span class="badge-warning">${l.status}</span>`;
            if (l.status === 'CRITICAL') statusBadge = `<span class="badge-critical">${l.status}</span>`;

            return `
                <tr>
                    <td style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted);">${new Date(l.timestamp).toLocaleTimeString()}</td>
                    <td style="font-weight: 700; font-size: 0.8rem; font-family: var(--font-mono);">${l.event_type}</td>
                    <td style="font-size: 0.82rem;">${l.user_name ? `${l.user_name} (${l.employee_id || ''})` : '<span style="color:var(--text-muted);">Unidentified / System</span>'}</td>
                    <td style="font-size: 0.8rem; color: var(--text-secondary);">${l.details}</td>
                    <td>${statusBadge}</td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        console.error("Failed to load audit logs:", e);
    }
}

// --- Settings Operations ---

async function loadSettings() {
    try {
        const res = await fetch('/api/settings');
        const data = await res.json();

        window.adminAlertEmail = data.admin_alert_email || 'poharekulbhushan2006@gmail.com';
        window.adminPhoneNumber = data.admin_phone_number || '9834481366';

        document.getElementById('setAdminEmail').value = window.adminAlertEmail;
        const phoneEl = document.getElementById('setAdminPhone');
        if (phoneEl) phoneEl.value = window.adminPhoneNumber;
        document.getElementById('setSmtpHost').value = data.smtp_host || '';
        document.getElementById('setSmtpPort').value = data.smtp_port || '587';
        document.getElementById('setSmtpUser').value = data.smtp_user || '';
        document.getElementById('setSmtpFrom').value = data.smtp_from || '';
        document.getElementById('setFaceThreshold').value = data.face_threshold || 0.55;
        document.getElementById('threshVal').textContent = data.face_threshold || 0.55;
        document.getElementById('setAutoLockSec').value = data.auto_lock_seconds || 10;
    } catch (e) {
        console.error("Failed to load settings:", e);
    }
}

async function handleSettingsSubmit(e) {
    e.preventDefault();
    const phoneVal = document.getElementById('setAdminPhone') ? document.getElementById('setAdminPhone').value.trim() : '9834481366';
    const emailVal = document.getElementById('setAdminEmail').value.trim();

    const payload = {
        admin_alert_email: emailVal,
        admin_phone_number: phoneVal,
        smtp_host: document.getElementById('setSmtpHost').value,
        smtp_port: document.getElementById('setSmtpPort').value,
        smtp_user: document.getElementById('setSmtpUser').value,
        smtp_password: document.getElementById('setSmtpPassword').value || null,
        smtp_from: document.getElementById('setSmtpFrom').value,
        face_threshold: parseFloat(document.getElementById('setFaceThreshold').value),
        auto_lock_seconds: parseInt(document.getElementById('setAutoLockSec').value)
    };

    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            window.adminAlertEmail = emailVal;
            window.adminPhoneNumber = phoneVal;
            alert("Security Alert & Contact settings saved successfully!");
            loadAuditLogs();
        }
    } catch (err) {
        alert("Failed to save settings: " + err.message);
    }
}

async function sendTestAlertEmail() {
    const email = document.getElementById('setAdminEmail').value;
    if (!email) {
        alert("Please enter a valid alert recipient email first.");
        return;
    }

    try {
        const res = await fetch('/api/test-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recipient: email })
        });
        const result = await res.json();
        alert(`Test Alert Result: [${result.status.toUpperCase()}]\n${result.message}`);
        loadAuditLogs();
    } catch (e) {
        alert("Failed to dispatch test email: " + e.message);
    }
}

// --- Security Officer Master Passkey Gate ---

function checkAdminGate() {
    if (sessionStorage.getItem('antra_admin_token') !== 'active') {
        const gate = document.getElementById('adminGateModal');
        if (gate) {
            gate.style.display = 'flex';
            setTimeout(() => {
                const inp = document.getElementById('gatePasskeyInput');
                if (inp) inp.focus();
            }, 100);
        }
    }
}

async function handleGateAuth(e) {
    if (e) e.preventDefault();
    const input = document.getElementById('gatePasskeyInput');
    const err = document.getElementById('gateAuthError');
    const passkey = input ? input.value.trim() : '';

    if (!passkey) return;

    try {
        const res = await fetch('/api/admin-auth', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ passkey: passkey })
        });
        const data = await res.json();
        if (res.ok && data.authenticated) {
            sessionStorage.setItem('antra_admin_token', 'active');
            const gate = document.getElementById('adminGateModal');
            if (gate) gate.style.display = 'none';
        } else {
            if (err) {
                err.textContent = "Clearance Denied: Invalid Master Passkey";
                err.style.display = 'block';
            }
        }
    } catch (ex) {
        if (err) {
            err.textContent = "Authentication failed: " + ex.message;
            err.style.display = 'block';
        }
    }
}

function lockAndExitAdmin() {
    sessionStorage.removeItem('antra_admin_token');
    window.location.href = '/';
}

document.addEventListener('DOMContentLoaded', initAdmin);

