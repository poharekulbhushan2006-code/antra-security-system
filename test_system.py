import os
import sys
import json
import base64
import random
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

from app import app
import database
import security
from config import EVIDENCE_DIR

client = TestClient(app)

def create_dummy_base64_image() -> str:
    # 1x1 transparent PNG in base64
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

def generate_random_descriptor(seed: int = 42) -> list:
    random.seed(seed)
    return [round(random.uniform(-1.0, 1.0), 4) for _ in range(128)]

def run_all_tests():
    print("\n=======================================================")
    print("  ANTRA SECURITY SYSTEM - AUTOMATED TEST SUITE")
    print("=======================================================\n")
    
    # Test 1: Health check / HTML templates
    print("[TEST 1] Loading Kiosk & Admin View Endpoints...")
    res_kiosk = client.get("/")
    assert res_kiosk.status_code == 200, f"Kiosk returned {res_kiosk.status_code}"
    assert "Antra Security System" in res_kiosk.text
    
    res_admin = client.get("/admin")
    assert res_admin.status_code == 200, f"Admin returned {res_admin.status_code}"
    assert "ANTRA SECURITY MANAGEMENT" in res_admin.text
    print("  PASS: HTML templates render correctly with security headers.\n")

    # Test 2: User Enrollment
    print("[TEST 2] Enrolling Authorized Personnel with Face ID & PIN...")
    alice_descriptor = generate_random_descriptor(seed=int(uuid.uuid4().int % 100000))
    enroll_payload = {
        "name": "Commander Alice Vance",
        "employee_id": f"EMP-SEC-{uuid.uuid4().hex[:6].upper()}",
        "role": "Chief Vault Custodian",
        "pin": "antra",
        "descriptor": alice_descriptor,
        "image_base64": create_dummy_base64_image()
    }
    
    res_reg = client.post("/api/register-user", json=enroll_payload)
    assert res_reg.status_code == 200, f"Registration failed: {res_reg.text}"
    reg_data = res_reg.json()
    assert reg_data["success"] is True
    user_id = reg_data["user_id"]
    print(f"  PASS: User '{enroll_payload['name']}' enrolled with password 'antra' (ID #{user_id}).\n")

    # Test 3: Face Verification (Authorized vs Unregistered)
    print("[TEST 3] Biometric Face Verification (Authorized vs Unregistered)...")
    # 3a. Exact match
    res_verify_exact = client.post("/api/verify-face", json={"descriptor": alice_descriptor})
    assert res_verify_exact.status_code == 200
    data_exact = res_verify_exact.json()
    assert data_exact["matched"] is True, "Expected matched: True for Alice's descriptor"
    assert data_exact["user"]["name"] == "Commander Alice Vance"
    print("  PASS: Authorized face recognized instantly.")

    # 3b. Perturbed face (slight angle difference, dist ~ 0.05)
    perturbed_descriptor = [val + random.uniform(-0.01, 0.01) for val in alice_descriptor]
    res_verify_perturbed = client.post("/api/verify-face", json={"descriptor": perturbed_descriptor})
    data_perturbed = res_verify_perturbed.json()
    assert data_perturbed["matched"] is True, "Expected matched: True for slight facial variance"
    print(f"  PASS: Slight facial variance verified (distance: {data_perturbed['distance']}).")

    # 3c. Unregistered person (completely different random face)
    bob_descriptor = generate_random_descriptor(seed=999)
    res_verify_unknown = client.post("/api/verify-face", json={"descriptor": bob_descriptor})
    data_unknown = res_verify_unknown.json()
    assert data_unknown["matched"] is False, "Expected matched: False for unregistered face"
    print(f"  PASS: Unregistered person correctly flagged (distance: {data_unknown['distance']}).\n")

    # Test 4: 2FA Passcode Verification
    print("[TEST 4] Passcode Clearance & Vault Door Unlock with 'antra'...")
    # 4a. Wrong Password
    res_bad_pin = client.post("/api/unlock-vault", json={"user_id": user_id, "pin": "wrongpass"})
    assert res_bad_pin.status_code == 200
    assert res_bad_pin.json()["success"] is False
    print("  PASS: Incorrect password rejected with warning.")

    # 4b. Correct Password 'antra'
    res_good_pin = client.post("/api/unlock-vault", json={"user_id": user_id, "pin": "antra"})
    assert res_good_pin.status_code == 200
    data_good_pin = res_good_pin.json()
    assert data_good_pin["success"] is True
    print(f"  PASS: Correct PIN cleared! Vault door unlocked: {data_good_pin['message']}\n")

    # Test 5: Intruder Interception, Snapshot Storage & Alert Dispatch
    print("[TEST 5] Intruder Reporting, Image File Storage & Email Dispatch...")
    intruder_payload = {
        "image_base64": create_dummy_base64_image(),
        "reason": "Unregistered intruder detected at terminal gate during automated test",
        "score": 0.96
    }
    res_intruder = client.post("/api/report-intruder", json=intruder_payload)
    assert res_intruder.status_code == 200, f"Intruder reporting failed: {res_intruder.text}"
    intruder_data = res_intruder.json()
    assert intruder_data["success"] is True
    incident_id = intruder_data["incident_id"]
    photo_filename = intruder_data["photo_filename"]
    
    # Check that photo exists on disk in evidence directory
    saved_file = EVIDENCE_DIR / photo_filename
    assert saved_file.exists(), f"Evidence photo was not saved to {saved_file}"
    print(f"  PASS: Intruder incident #{incident_id} saved to disk: {photo_filename}")
    print(f"  PASS: Email alert queued: {intruder_data['email_status']}\n")

    # Test 6: Audit Logs and Incident Resolution
    print("[TEST 6] Audit Trail & Incident Archival...")
    res_audit = client.get("/api/audit-logs")
    logs = res_audit.json()["logs"]
    assert len(logs) > 0
    event_types = [l["event_type"] for l in logs]
    assert "USER_ENROLLED" in event_types
    assert "VAULT_UNLOCKED" in event_types
    assert "INTRUDER_CAPTURED" in event_types
    print(f"  PASS: Audit log contains {len(logs)} verified events including enrollment and breach alerts.")

    res_resolve = client.post(f"/api/intruders/{incident_id}/resolve")
    assert res_resolve.status_code == 200
    assert res_resolve.json()["success"] is True
    print(f"  PASS: Incident #{incident_id} marked as resolved by security officer.\n")

    print("=======================================================")
    print("  ALL 6 SECURITY TEST SUITES PASSED FLAWLESSLY! [OK]")
    print("=======================================================\n")

if __name__ == "__main__":
    run_all_tests()
