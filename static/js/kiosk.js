/**
 * AegisVault Kiosk Access Controller (High-Security Edition)
 * Enforces Two-Factor Authentication (Biometric Face ID + Cryptographic Passkey),
 * Drives Real-Time Cybernetic Telemetry, Kinetic Vault Door Mechanics,
 * Voice AI Assistant, and Autonomous Intruder Interception.
 */

const STATE = {
    IDLE: 'IDLE',
    PIN_REQUIRED: 'PIN_REQUIRED',
    VAULT_UNLOCKED: 'VAULT_UNLOCKED',
    INTRUDER_ALERT: 'INTRUDER_ALERT',
    LOCKOUT: 'LOCKOUT'
};

let currentState = STATE.IDLE;
let modelsLoaded = false;
let identifiedUser = null;
let autoLockTimer = null;
let scanInterval = null;
let lastIntruderReportTime = 0;
const INTRUDER_COOLDOWN_MS = 6000;

// DOM Elements
const videoEl = document.getElementById('cameraFeed');
const canvasEl = document.getElementById('cameraOverlay');
const statusBar = document.getElementById('statusBar');
const statusText = document.getElementById('statusText');
const statusSub = document.getElementById('statusSub');
const pinSection = document.getElementById('pinSection');
const pinUserName = document.getElementById('pinUserName');
const pinUserRole = document.getElementById('pinUserRole');
const vaultDoor = document.getElementById('vaultDoor');
const vaultStateBanner = document.getElementById('vaultStateBanner');
const vaultStateText = document.getElementById('vaultStateText');
const intruderBanner = document.getElementById('intruderBanner');
const intruderPreviewImg = document.getElementById('intruderPreviewImg');
const intruderBannerText = document.getElementById('intruderBannerText');
const perimeterStrobe = document.getElementById('perimeterStrobe');

// --- Initialization ---

async function initKiosk() {
    checkAdminSession();
    setStatus("INITIALIZING BIOMETRIC NEURAL MESH...", "idle", "WARMING UP TENSORFLOW");
    try {
        await faceapi.nets.tinyFaceDetector.loadFromUri('/static/models');
        await faceapi.nets.faceLandmark68Net.loadFromUri('/static/models');
        await faceapi.nets.faceRecognitionNet.loadFromUri('/static/models');
        modelsLoaded = true;
        console.log("✅ Biometric neural networks loaded.");

        await startCamera();
        setStatus("SYSTEM ARMED: POSITION FACE IN OPTICAL SENSOR", "idle", "SURVEILLANCE ACTIVE");

        startScanningLoop();
    } catch (err) {
        console.error("Initialization error:", err);
        setStatus("SENSOR / NEURAL NET INIT ERROR: " + err.message, "intruder", "HARDWARE FAULT");
    }
}

async function startCamera() {
    try {
        let stream = null;
        try {
            // Tier 1: Request Crisp High Definition (1080p / 720p) for crystal clear facial capture
            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1920, min: 1280 },
                    height: { ideal: 1080, min: 720 },
                    facingMode: 'user',
                    frameRate: { ideal: 30, max: 60 }
                },
                audio: false
            });
        } catch (hdErr) {
            console.warn("HD camera constraint not supported, trying standard definition...", hdErr);
            try {
                // Tier 2: Standard definition 640x480
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
                    audio: false
                });
            } catch (sdErr) {
                console.warn("Standard camera constraint failed, using generic video fallback...", sdErr);
                // Tier 3: Universal fallback
                stream = await navigator.mediaDevices.getUserMedia({
                    video: true,
                    audio: false
                });
            }
        }

        videoEl.srcObject = stream;
        return new Promise((resolve) => {
            videoEl.onloadedmetadata = () => {
                videoEl.play().catch(e => console.warn("video play catch:", e));
                canvasEl.width = videoEl.videoWidth || 640;
                canvasEl.height = videoEl.videoHeight || 480;
                resolve();
            };
            // Fallback if metadata event delayed
            setTimeout(() => {
                if (videoEl.videoWidth) {
                    canvasEl.width = videoEl.videoWidth;
                    canvasEl.height = videoEl.videoHeight;
                }
                resolve();
            }, 1500);
        });
    } catch (err) {
        console.error("Direct camera access failed:", err);
        let errorMsg = "Optical sensor error: " + (err.message || err.name);
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
            errorMsg = "Webcam permission pending. Please enable camera in browser settings.";
        } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
            errorMsg = "Webcam in use by another app. Close background camera apps and reload.";
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
            errorMsg = "No webcam device detected. Please connect or enable your camera.";
        }
        
        setStatus(errorMsg, "intruder", "HARDWARE STATUS");
        // Do NOT show blocking alert dialog - keep interface seamless and responsive
        throw err;
    }
}

// --- Face Detection & Tracking Loop ---

function startScanningLoop() {
    if (scanInterval) clearInterval(scanInterval);

    scanInterval = setInterval(async () => {
        if (!modelsLoaded || currentState === STATE.VAULT_UNLOCKED || currentState === STATE.LOCKOUT) {
            return;
        }

        try {
            // Enhanced inputSize (320) for sharper, higher-precision facial feature extraction
            const detection = await faceapi
                .detectSingleFace(videoEl, new faceapi.TinyFaceDetectorOptions({ inputSize: 320, scoreThreshold: 0.5 }))
                .withFaceLandmarks()
                .withFaceDescriptor();

            const ctx = canvasEl.getContext('2d');
            ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);

            if (detection) {
                drawBiometricReticle(ctx, detection);

                if (currentState === STATE.IDLE) {
                    await processDetectedFace(detection);
                }
            }
        } catch (err) {
            console.error("Scan error:", err);
        }
    }, 320);
}

function drawBiometricReticle(ctx, detection) {
    const { x, y, width, height } = detection.detection.box;
    const isAlert = (currentState === STATE.INTRUDER_ALERT);

    ctx.strokeStyle = isAlert ? '#ff0055' : '#00f0ff';
    ctx.lineWidth = 2;
    ctx.shadowColor = ctx.strokeStyle;
    ctx.shadowBlur = 10;

    // Outer Target Reticle Brackets
    const bLen = Math.min(width, height) * 0.22;
    ctx.beginPath();
    ctx.moveTo(x, y + bLen); ctx.lineTo(x, y); ctx.lineTo(x + bLen, y);
    ctx.moveTo(x + width - bLen, y); ctx.lineTo(x + width, y); ctx.lineTo(x + width, y + bLen);
    ctx.moveTo(x, y + height - bLen); ctx.lineTo(x, y + height); ctx.lineTo(x + bLen, y + height);
    ctx.moveTo(x + width - bLen, y + height); ctx.lineTo(x + width, y + height); ctx.lineTo(x + width, y + height - bLen);
    ctx.stroke();

    // Center Crosshair
    const cx = x + width / 2;
    const cy = y + height / 2;
    ctx.beginPath();
    ctx.arc(cx, cy, 4, 0, Math.PI * 2);
    ctx.stroke();

    // 68 Landmark Cybernetic Dots
    if (detection.landmarks) {
        ctx.fillStyle = isAlert ? 'rgba(255, 0, 85, 0.8)' : 'rgba(0, 240, 255, 0.65)';
        detection.landmarks.positions.forEach(pt => {
            ctx.fillRect(pt.x - 1, pt.y - 1, 2, 2);
        });
    }

    ctx.shadowBlur = 0;
}

// --- Face Verification & Access Decision ---

async function processDetectedFace(detection) {
    const descriptorArray = Array.from(detection.descriptor);

    try {
        const response = await fetch('/api/verify-face', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ descriptor: descriptorArray })
        });
        const data = await response.json();

        if (data.matched) {
            // AUTHORIZED IDENTITY! Proceed to Factor 2 Passkey
            identifiedUser = data.user;
            transitionToPinState(data.user);
        } else {
            // UNREGISTERED PERSON -> INTRUSION INTERCEPTION!
            const now = Date.now();
            if (now - lastIntruderReportTime > INTRUDER_COOLDOWN_MS) {
                lastIntruderReportTime = now;
                await handleIntruderInterception(detection);
            }
        }
    } catch (err) {
        console.error("Biometric verification error:", err);
    }
}

// --- Intruder Breach Interception ---

async function handleIntruderInterception(detection) {
    currentState = STATE.INTRUDER_ALERT;
    window.vaultAudio.startIntruderAlarm(5);
    window.vaultAudio.speak("Warning! Security breach. Unregistered personnel detected. Intruder photograph logged and dispatched.", true);

    const snapshotBase64 = captureCameraFrame();

    setStatus("🚨 SECURITY BREACH: UNREGISTERED PERSON DETECTED! EVIDENCE LOGGED & DISPATCHED!", "intruder", "THREAT LEVEL: CRITICAL");
    vaultDoor.classList.add('breach');
    if (perimeterStrobe) perimeterStrobe.classList.add('active');

    intruderPreviewImg.src = snapshotBase64;
    intruderBannerText.innerHTML = `<strong>CRITICAL SECURITY BREACH:</strong> Unregistered face intercepted.<br>Snapshot logged & emergency alert email dispatched to bank security operations.`;
    intruderBanner.classList.add('active');

    try {
        const res = await fetch('/api/report-intruder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image_base64: snapshotBase64,
                reason: 'Unregistered face attempted unauthorized access at vault entrance',
                score: detection ? detection.detection.score : 0.95
            })
        });
        const result = await res.json();
        console.log("Intruder incident dispatched:", result);
    } catch (e) {
        console.error("Failed to transmit intruder incident:", e);
    }

    setTimeout(() => {
        intruderBanner.classList.remove('active');
        vaultDoor.classList.remove('breach');
        if (perimeterStrobe) perimeterStrobe.classList.remove('active');
        if (currentState === STATE.INTRUDER_ALERT) {
            resetToIdle();
        }
    }, 6500);
}

function captureCameraFrame() {
    if (!videoEl || !videoEl.videoWidth || !videoEl.videoHeight) {
        return "";
    }
    const offscreen = document.createElement('canvas');
    offscreen.width = videoEl.videoWidth;
    offscreen.height = videoEl.videoHeight;
    const ctx = offscreen.getContext('2d');
    
    // Superior image smoothing and clarity preservation
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    
    // Mirror horizontally so the saved snapshot matches natural perspective
    ctx.translate(offscreen.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(videoEl, 0, 0, offscreen.width, offscreen.height);
    
    // High-definition JPEG (0.96 quality)
    return offscreen.toDataURL('image/jpeg', 0.96);
}

// --- Factor 2: Security Passkey Verification ---

function transitionToPinState(user) {
    currentState = STATE.PIN_REQUIRED;
    window.vaultAudio.playScanChirp();
    window.vaultAudio.speak(`Identity confirmed. Welcome, ${user.name}. Please enter your security passkey.`);

    setStatus(`IDENTITY VERIFIED: ${user.name} — ENTER PASSKEY`, "verified");
    pinUserName.textContent = user.name;
    pinUserRole.textContent = `${user.role} // CLEARANCE GRANTED`;
    
    const passInput = document.getElementById('vaultPasswordInput');
    if (passInput) {
        passInput.value = '';
        setTimeout(() => passInput.focus(), 150);
    }
    pinSection.classList.add('active');
}

function handleKeypadPress(val) {
    window.vaultAudio.playKeypadBeep();
    const passInput = document.getElementById('vaultPasswordInput');

    if (val === 'clear') {
        if (passInput) passInput.value = '';
        return;
    }

    if (val === 'enter') {
        submitPinVerification();
        return;
    }

    if (passInput) {
        passInput.value += val;
        passInput.focus();
    }
}

function togglePasswordVisibility() {
    const passInput = document.getElementById('vaultPasswordInput');
    if (passInput) {
        passInput.type = (passInput.type === 'password') ? 'text' : 'password';
    }
}

async function submitPinVerification() {
    const passInput = document.getElementById('vaultPasswordInput');
    const enteredPass = passInput ? passInput.value.trim() : '';

    if (!identifiedUser || enteredPass.length < 3) {
        alert("Please enter a valid security passkey (at least 3 characters).");
        if (passInput) passInput.focus();
        return;
    }

    setStatus("VERIFYING DUAL-FACTOR CREDENTIALS...", "idle");
    const snapshot = captureCameraFrame();

    try {
        const response = await fetch('/api/unlock-vault', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: identifiedUser.id,
                pin: enteredPass,
                snapshot_base64: snapshot
            })
        });

        if (!response.ok) {
            let errMsg = `Server returned HTTP ${response.status}`;
            try {
                const errData = await response.json();
                errMsg = errData.detail || errData.message || errMsg;
            } catch (_) {}
            window.vaultAudio.playDeniedBuzzer();
            setStatus(`GATEWAY ERROR: ${errMsg}`, "intruder");
            return;
        }

        const data = await response.json();

        if (data.success) {
            triggerVaultUnlock(data.message, data.auto_lock_seconds);
        } else {
            window.vaultAudio.playDeniedBuzzer();
            window.vaultAudio.speak("Security passkey rejected.");

            if (passInput) {
                passInput.value = '';
                passInput.focus();
            }

            if (data.lockout) {
                currentState = STATE.LOCKOUT;
                window.vaultAudio.startIntruderAlarm(6);
                window.vaultAudio.speak("Emergency lockout engaged. Security dispatched.", true);

                setStatus(`🚨 EMERGENCY LOCKOUT: Excessive failed attempts!`, "intruder");
                vaultDoor.classList.add('breach');
                if (perimeterStrobe) perimeterStrobe.classList.add('active');
                pinSection.classList.remove('active');

                setTimeout(() => {
                    vaultDoor.classList.remove('breach');
                    if (perimeterStrobe) perimeterStrobe.classList.remove('active');
                    resetToIdle();
                }, 15000);
            } else {
                setStatus(`ACCESS DENIED: ${data.message}`, "intruder");
            }
        }
    } catch (err) {
        console.error("Unlock error:", err);
        setStatus(`SECURITY GATEWAY ERROR: ${err.message || "Connection failed"}`, "intruder");
    }
}

// --- Kinetic Vault Door Unlock Sequence ---

function triggerVaultUnlock(welcomeMessage, autoLockSeconds = 10) {
    currentState = STATE.VAULT_UNLOCKED;
    pinSection.classList.remove('active');

    window.vaultAudio.playGrantedChime();
    window.vaultAudio.speak("Access granted. Vault door disengaged.");

    vaultDoor.classList.add('unlocked');
    if (vaultStateText) {
        vaultStateText.textContent = "UNLOCKED // OPEN";
        vaultStateText.style.color = "var(--emerald-bright)";
    }

    setStatus(`✅ 2FA AUTHORIZED: ${welcomeMessage}`, "verified");

    let remaining = autoLockSeconds;
    if (autoLockTimer) clearInterval(autoLockTimer);

    autoLockTimer = setInterval(() => {
        remaining -= 1;
        if (vaultStateText) {
            vaultStateText.textContent = `UNLOCKED (RELOCK IN ${remaining}s)`;
        }
        if (remaining <= 0) {
            clearInterval(autoLockTimer);
            relockVault();
        }
    }, 1000);
}

function relockVault() {
    window.vaultAudio.playScanChirp();
    window.vaultAudio.speak("Auto-lock engaged. Vault secured.");

    vaultDoor.classList.remove('unlocked');
    if (vaultStateText) {
        vaultStateText.textContent = "SECURE // SEALED";
        vaultStateText.style.color = "#f87171";
    }

    resetToIdle();
}

function resetToIdle() {
    currentState = STATE.IDLE;
    identifiedUser = null;
    const passInput = document.getElementById('vaultPasswordInput');
    if (passInput) passInput.value = '';
    pinSection.classList.remove('active');
    if (perimeterStrobe) perimeterStrobe.classList.remove('active');
    setStatus("SYSTEM ARMED: POSITION FACE IN IRIS SENSOR", "idle");
}

function cancelPinAuth() {
    resetToIdle();
}

function setStatus(text, stateType) {
    statusText.textContent = text;
    statusBar.className = 'scan-status-badge ' + (stateType === 'verified' ? 'verified' : (stateType === 'intruder' ? 'intruder' : ''));
}

// --- Keyboard Support & Secret Admin Hotkeys ---

window.addEventListener('keydown', (e) => {
    if (currentState === STATE.PIN_REQUIRED) {
        if (e.key === 'Enter') {
            e.preventDefault();
            submitPinVerification();
        } else if (e.key === 'Escape') {
            cancelPinAuth();
        }
    }

    // Secret Admin Shortcut: Ctrl + Shift + A or Ctrl + Alt + A
    if ((e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'a') || (e.ctrlKey && e.altKey && e.key.toLowerCase() === 'a')) {
        e.preventDefault();
        openAdminAuthModal();
    }
});

// --- Security Officer & Admin Console Access ---
let emblemClickCount = 0;
let emblemClickTimer = null;

function handleAdminEmblemClick() {
    emblemClickCount++;
    if (emblemClickTimer) clearTimeout(emblemClickTimer);

    if (emblemClickCount >= 3) {
        emblemClickCount = 0;
        openAdminAuthModal();
    } else {
        emblemClickTimer = setTimeout(() => {
            emblemClickCount = 0;
        }, 1200);
    }
}

function handleAdminConsoleClick(e) {
    if (sessionStorage.getItem('antra_admin_token') === 'active') {
        // Already authenticated, proceed directly to /admin
        return true;
    }
    // Intercept click: prompt for Master Passkey
    if (e) e.preventDefault();
    openAdminAuthModal();
}

function openAdminAuthModal() {
    const modal = document.getElementById('adminAuthModal');
    if (!modal) return;
    const input = document.getElementById('adminPasskeyInput');
    const err = document.getElementById('adminAuthError');
    if (err) err.style.display = 'none';
    if (input) input.value = '';
    modal.style.display = 'flex';
    setTimeout(() => input && input.focus(), 150);
}

function closeAdminAuthModal() {
    const modal = document.getElementById('adminAuthModal');
    if (modal) modal.style.display = 'none';
}

async function submitAdminSecretAuth(e) {
    if (e) e.preventDefault();
    const input = document.getElementById('adminPasskeyInput');
    const err = document.getElementById('adminAuthError');
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
            checkAdminSession();
            closeAdminAuthModal();
            setStatus("SECURITY CLEARANCE VERIFIED // OPENING ADMIN CONSOLE...", "verified");
            if (window.vaultAudio) {
                window.vaultAudio.playGrantedChime();
                window.vaultAudio.speak("Security clearance verified. Opening admin console.");
            }
            setTimeout(() => {
                window.location.href = '/admin';
            }, 400);
        } else {
            if (err) {
                err.textContent = "Clearance Denied: Invalid Master Passkey";
                err.style.display = 'block';
            }
            if (window.vaultAudio) window.vaultAudio.playDeny();
        }
    } catch (errExp) {
        if (err) {
            err.textContent = "Authentication failed: " + errExp.message;
            err.style.display = 'block';
        }
    }
}

function lockAdminConsole() {
    sessionStorage.removeItem('antra_admin_token');
    checkAdminSession();
    setStatus("ADMIN CONSOLE LOCKED // PASSWORD REQUIRED TO OPEN", "idle");
    if (window.vaultAudio) {
        window.vaultAudio.playScanChirp();
        window.vaultAudio.speak("Admin session locked.");
    }
}

function checkAdminSession() {
    const link = document.getElementById('adminConsoleLink');
    const lockBtn = document.getElementById('adminLockBtn');
    if (link) {
        link.style.display = 'inline-flex'; // Openly visible on page
    }
    if (lockBtn) {
        lockBtn.style.display = (sessionStorage.getItem('antra_admin_token') === 'active') ? 'inline-flex' : 'none';
    }
}

document.addEventListener('DOMContentLoaded', initKiosk);

