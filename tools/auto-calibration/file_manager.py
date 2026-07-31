import os
import requests
from pathlib import Path

def upload(esp_ip, local_path, dir, file):
    """
    Deletes the existing file and uploads the new one to the ESP32 SD card.
    Uses raw binary payload as required by AI on the Edge firmware.
    """
    
    delete_url = f"http://{esp_ip}/delete/{dir}/{file}"
    upload_url = f"http://{esp_ip}/upload/{dir}/{file}"
    
    try:
        print(f"[*] Deleting '{file}' on ESP32 ({esp_ip})...")
        requests.post(delete_url, timeout=10)
        
        if Path(local_path).is_file():
            print(f"[*] Uploading new '{file}'...")
            with open(local_path, 'rb') as f:
                binary_data = f.read()
            
            headers = {'Content-Type': 'application/octet-stream'}
            res = requests.post(upload_url, data=binary_data, headers=headers, timeout=15)
            
            if res.status_code == 200:
                print(f"[+] File '{file}' uploaded successfully.")
                return True
            else:
                print(f"[-] Upload error on ESP32: {res.text}")
                return False
        else:
            print(f"[-] The file '{local_path}' does not exist.")
            return False
            
    except Exception as e:
        print(f"[-] Connection error to ESP32: {e}")
        return False
    
def download(esp_ip, remote_path, local_path):
    """
    Downloads a file from the ESP32 SD card to the local machine.
    """
    url = f"http://{esp_ip}/fileserver{remote_path}"
    
    try:
        print(f"[*] Downloading '{remote_path}' from ESP32 ({esp_ip})...")
        res = requests.get(url, timeout=10)
        
        if res.status_code == 200:
            if os.path.dirname(local_path):
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as f:
                f.write(res.content)
            print(f"[+] File '{local_path}' downloaded successfully.")
            return True
        else:
            print(f"[-] Download error on ESP32: {res.text}")
            return False
            
    except Exception as e:
        print(f"[-] Connection error to ESP32: {e}")
        return False