# 🛡️ AegisVault — Biometric & Multi-Factor Access Security System

A high-security biometric and passcode access control system engineered for bank vaults, precious material reserves, and high-value secure storage facilities.

---

## 🌟 Key Highlights & Security Architecture

1. **Two-Factor Authentication (2FA) Gate**:
   - **Factor 1: Biometric Face Recognition**:
     - Real-time 60 FPS face detection and 128-dimensional deep metric feature extraction using client-side neural networks (`TinyFaceDetector` + `FaceRecognitionNet`).
     - Fast Euclidean distance comparison against registered personnel.
   - **Factor 2: Cryptographic Security PIN / Passcode**:
     - Passwords and PINs are cryptographically hashed using PBKDF2 HMAC SHA-256 with 100,000 iterations and unique 32-byte salts.
     - Access is strictly gated: **Both Face ID and Passcode are mandatory to unlock the vault**.

2. **Intruder Detection & Autonomous Photographic Interception**:
   - When an **unregistered face** attempts access:
     - Instantly captures a high-resolution photographic snapshot of the intruder.
     - Dispatches an **urgent security breach email** with the intruder's photo attached and embedded inline.
     - Logs the incident to the secure Evidence Vault with exact timestamp, detection confidence, and threat level (`CRITICAL`).
     - Triggers audible siren deterrent and high-threat flashing alert on screen.
   - If an authorized person's face is recognized but the **PIN is entered incorrectly 3 times**:
     - Locks the kiosk and treats the event as potential coercion or identity compromise, immediately photographing the suspect and dispatching an alarm email.

3. **Administration & Evidence Vault (`/admin`)**:
   - **Personnel Enrollment Wizard**: Enroll bank managers and vault custodians with live camera face scanning and secret PINs.
   - **Intruder Evidence Vault**: Interactive photo gallery of all intercepted intruders with full-screen inspection modal and status management.
   - **Security Audit Logs**: Cryptographic timestamped event trail of all entries, failures, enrollments, and alerts.
   - **Email & Sensitivity Settings**: Configure alert recipient email, SMTP server credentials, face match strictness threshold, and auto-lock timeout.

4. **Realistic Bank Vault Interface & Sound FX**:
   - Obsidian dark mode glassmorphism UI with cybernetic HUD overlays.
   - Armored circular vault door with central 3-spoke wheel and 4 pneumatic locking bolts that mechanically retract upon clearance.
   - Integrated Web Audio API synthesizer for biometric scanning chirps, hydraulic door release rumbles, chime harmonics, and intruder sirens.

---

## 🚀 Quick Start Guide

### 1. Launch the Security System
Run the Python launcher in your terminal:
```powershell
.venv\Scripts\python run.py
```
*(Or double-click `start_vault.bat` in Windows Explorer).*

### 2. Open in Your Browser
- **Bank Vault Kiosk Terminal**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Security Admin & Evidence Vault**: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)

---

## 📖 How to Use the System

### Step 1: Enroll Authorized Personnel
1. Go to [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin) and select the **Personnel Enrollment** tab.
2. Enter the personnel's name (e.g., `Sarah Connor`), Employee ID (e.g., `EMP-101`), Role, and a 4-to-8 digit PIN (e.g., `1234`).
3. Click **Start Camera**, align your face in the box, and click **Scan & Lock Face ID**.
4. Click **Register & Enroll Personnel**.

### Step 2: Test Authorized Vault Unlock (2FA)
1. Navigate back to the **Kiosk Terminal** ([http://127.0.0.1:8000](http://127.0.0.1:8000)).
2. Look directly into the camera.
3. The biometric reticle will track your face and verify your identity (`IDENTITY VERIFIED: [Name]`).
4. The security PIN pad will slide into view.
5. Enter your PIN (`1234`) and press **ENT** (or press Enter on your keyboard).
6. **Access Granted!** The central vault wheel rotates, locking bolts retract, hydraulic chime sounds, and the vault opens with an auto-lock countdown timer.

### Step 3: Test Intruder Capture & Alert Dispatch
1. Have an unregistered person look at the camera (or click the **Simulate Intruder Capture** test button).
2. The system detects an **unregistered face**:
   - Emergency siren sounds.
   - A high-resolution snapshot is captured instantly.
   - A critical intrusion alert banner displays with the intruder's photo.
   - An alert email with the photo attachment is dispatched to the security officer.
3. Check the **Intruder Evidence Vault** at `/admin` to inspect the captured intruder photo and incident details!

---

## 📧 Email Alert Setup (Real-World SMTP)

To receive real email alerts when an unregistered person is captured:
1. Open [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin) and click **Email & Alert Settings**.
2. Enter your email settings:
   - **Recipient Email**: The address where you want to receive alerts (e.g., `your_email@gmail.com`).
   - **SMTP Host**: `smtp.gmail.com`
   - **SMTP Port**: `587`
   - **SMTP User**: Your Gmail address.
   - **SMTP Password**: A 16-character **Google App Password** (generate via Google Account -> Security -> 2-Step Verification -> App Passwords).
3. Click **Save Settings** and test using the **Send Test Email** button.

*(Note: If SMTP is left unconfigured, the system automatically runs in **Simulation Mode** — photos are still captured, logged to disk, and displayed in the Evidence Vault).*

---

## 🧪 Running Automated Tests

A complete automated security test suite is included:
```powershell
.venv\Scripts\python test_system.py
```
This verifies:
- Template rendering and security headers
- User enrollment and cryptographic salt/hash verification
- Biometric cosine/Euclidean distance matching (exact, variance, and unknown rejection)
- 2FA PIN verification and lockout thresholds
- Intruder photo capture and filesystem storage
- Audit log persistence and incident resolution
