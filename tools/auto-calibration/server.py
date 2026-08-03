import os
import time
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, Security, UploadFile, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from image_processor import process_image
from file_manager import upload, download

load_dotenv()

app = FastAPI()
esp_ip = os.getenv("ESP32_IP")
PORT = int(os.getenv("PORT"))
TOKEN = os.getenv("API_TOKEN")
API_KEY_SCHEME = APIKeyHeader(name="X-API-Key", auto_error=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def auth(api_key_header: str = Security(API_KEY_SCHEME)):
    if not api_key_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-API-Key header required")
    if api_key_header != TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
    return api_key_header
    
@app.post("/get-photo")
async def get_photo(file: UploadFile = File(...)):
    """
    Endpoint triggered by ESP32. Receives the meter image, processes it via YOLO,
    updates configurations, synchronizes the SD card, and gracefully reboots the device.
    """
    dest_dir = "imgs"
    
    image_bytes = await file.read()
    os.makedirs(dest_dir, exist_ok=True)
    
    full_path = os.path.join(dest_dir, file.filename)
    with open(full_path, "wb") as f:
        f.write(image_bytes)
        
    try:
        config_file = download(esp_ip,"/config/config.ini", "config/config.ini")
        if not config_file:
            raise Exception("[-] Could not download config.ini from ESP32.")
        
        # yolo_data = process_image(full_path, dest_dir)
        yolo_data = process_image("water_meter.jpg", dest_dir)
        
        # Sync updated config
        config_sync = upload(esp_ip, "config/config.ini", "config", "config.ini")
        if not config_sync:
            raise Exception("[-] Config.ini upload failed.")

        for ref_path in yolo_data.get("ref_paths", []):
            ref_filename = os.path.basename(ref_path)
            upload(esp_ip, ref_path, "config", ref_filename)
            
        # Upload full image as background reference
        upload(esp_ip, full_path, "config", "reference.jpg")
        
        # Buffer time to allow SD Card IO operations to complete
        time.sleep(3)
        
        # Trigger ESP32 Reboot
        response = requests.get(f"http://{esp_ip}/reboot", timeout=10)
        if response.status_code in [200, 201]:
            print("[+] Reboot signal sent successfully.")
        else:
            print(f"[-] Failed to reboot. HTTP Status: {response.status_code}")
            
        return {"status": "success", "yolo_data": yolo_data, "esp32_sync": "ok"}
        
    except Exception as e:
        print(f"[-] Error: {str(e)}")
        return {"status": "error", "detail": str(e)}
    
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)