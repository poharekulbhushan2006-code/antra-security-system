import sys
import uvicorn

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("   ANTRA BIOMETRIC & MULTI-FACTOR SECURITY SYSTEM")
    print("=" * 65)
    print("  [+] Kiosk Terminal Interface:  http://127.0.0.1:8000")
    print("  [+] Security Admin & Evidence: http://127.0.0.1:8000/admin")
    print("=" * 65 + "\n")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
