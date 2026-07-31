import os
import cv2
from ultralytics import YOLO

MODEL_PATH = "best.pt"
model = YOLO(MODEL_PATH)

def process_image(image_path, output_dir):
    """
    Runs YOLO inference on the target image, categorizes objects (digits, analogs, markers),
    crops alignment references, and triggers the config update.
    Returns tracking data and paths to the generated reference images.
    """
    results = model(image_path)
    
    # Save debug image with bounding boxes
    debug_img = f"{os.path.splitext(image_path)[0]}_result.jpg"
    results[0].save(filename=debug_img)
    print(f"[+] Debug image saved at: {debug_img}")

    original_image = cv2.imread(image_path)

    digits = []
    analogs = []
    markers = []

    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        confidence = float(box.conf[0])
        class_name = model.names[int(box.cls[0])].lower()
        
        if 'analog' in class_name:
            analogs.append({"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1})
        elif 'digit' in class_name:
            digits.append({"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1})
        elif 'marker' in class_name or 'ref' in class_name:
            center_x, center_y = int((x1 + x2) / 2), int((y1 + y2) / 2)
            markers.append({
                "x": center_x, "y": center_y, 
                "conf": confidence,
                "box_x1": x1, "box_y1": y1, "box_x2": x2, "box_y2": y2
            })

    # Keep only the two highest confidence markers
    if len(markers) > 2:
        markers = sorted(markers, key=lambda m: m['conf'], reverse=True)[:2]

    # Sort elements (left to right)
    digits = sorted(digits, key=lambda d: d['x'])
    analogs = sorted(analogs, key=lambda a: a['x'])
    markers = sorted(markers, key=lambda m: m['x'])

    generated_refs = []
    os.makedirs(output_dir, exist_ok=True)

    for i, m in enumerate(markers):
        crop = original_image[m['box_y1']:m['box_y2'], m['box_x1']:m['box_x2']]
        ref_filename = f"ref{i}.jpg"
        ref_path = os.path.join(output_dir, ref_filename)
        cv2.imwrite(ref_path, crop)
        generated_refs.append(ref_path)

    print(f"\n[+] Found: {len(digits)} digits, {len(analogs)} analogs, {len(markers)} markers.")
    
    # Update the local ini configuration
    write_config(analogs, digits, markers, "config/config.ini")
    
    return {
        "digits_found": len(digits),
        "analogs_found": len(analogs),
        "markers_found": len(markers),
        "ref_paths": generated_refs
    }
    
def write_config(analogs, digits, markers, config_path):
    """
    Reads the local config.ini file and updates the [Digits], [Analog], 
    and [Alignment] sections with newly detected coordinates.
    """
    if not os.path.exists(config_path):
        print(f"Error: Base configuration file '{config_path}' not found.")
        return

    with open(config_path, "r") as f:
        lines = f.readlines()

    new_lines = []
    current_section = ""
    sections = {"Digits": False, "Analog": False, "Alignment": False}

    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith("[") and stripped.endswith("]"):
            if current_section == "Digits" and not sections["Digits"]:
                for i, d in enumerate(digits):
                    new_lines.append(f"main.dig{i+1} {d['x']} {d['y']} {d['width']} {d['height']} false\n")
                sections["Digits"] = True
            elif current_section == "Analog" and not sections["Analog"]:
                for i, a in enumerate(analogs):
                    name = "main.ana" if len(analogs) == 1 else f"main.ana{i+1}"
                    new_lines.append(f"{name} {a['x']} {a['y']} {a['width']} {a['height']} false\n")
                sections["Analog"] = True
            elif current_section == "Alignment" and not sections["Alignment"]:
                for i, m in enumerate(markers):
                    new_lines.append(f"/config/ref{i}.jpg {m['x']} {m['y']}\n")
                sections["Alignment"] = True
            
            current_section = stripped[1:-1]
            new_lines.append(line)
            continue

        # Skip previous (if presents) ROI lines to prevent duplication
        if current_section == "Digits" and stripped.startswith("main.dig"):
            continue
        if current_section == "Analog" and stripped.startswith("main.ana"):
            continue
        if current_section == "Alignment" and stripped.startswith("/config/ref"):
            continue

        new_lines.append(line)

    # Catch cases where the target section is the last one in the file
    if current_section == "Digits" and not sections["Digits"]:
        for i, d in enumerate(digits):
            new_lines.append(f"main.dig{i+1} {d['x']} {d['y']} {d['width']} {d['height']} false\n")
    elif current_section == "Analog" and not sections["Analog"]:
        for i, a in enumerate(analogs):
            name = "main.ana" if len(analogs) == 1 else f"main.ana{i+1}"
            new_lines.append(f"{name} {a['x']} {a['y']} {a['width']} {a['height']} false\n")
    elif current_section == "Alignment" and not sections["Alignment"]:
        for i, m in enumerate(markers):
            new_lines.append(f"/config/ref{i}.jpg {m['x']} {m['y']}\n")

    with open(config_path, "w") as f:
        f.writelines(new_lines)
        
    print("[+] Configs written.")