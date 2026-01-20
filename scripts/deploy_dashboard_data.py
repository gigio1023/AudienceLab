import json
import os
import shutil
import glob
from pathlib import Path
from datetime import datetime

# Absolute paths
SOURCE_DIR = Path("/Users/user/git/AudienceLab/agent/outputs/multi_agent_test")
TARGET_DIR = Path("/Users/user/git/AudienceLab/search-dashboard/public/simulation")
IMAGES_DIR = TARGET_DIR / "images"

def main():
    if not SOURCE_DIR.exists():
        print(f"Source directory {SOURCE_DIR} does not exist.")
        return

    # Clean target
    if IMAGES_DIR.exists():
        shutil.rmtree(IMAGES_DIR)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    agent_files = []
    
    # Iterate over agent directories
    for agent_dir in SOURCE_DIR.iterdir():
        if not agent_dir.is_dir():
            continue
            
        agent_id = agent_dir.name
        jsonl_path = agent_dir / "actions.jsonl"
        
        if not jsonl_path.exists():
            continue
            
        print(f"Processing {agent_id}...")
        
        # Create image subdir for this agent
        agent_img_dir = IMAGES_DIR / agent_id
        agent_img_dir.mkdir(exist_ok=True)
        
        # Copy all images and map them
        images_map = {} # step -> image_filename
        for img_path in agent_dir.glob("*.png"):
            shutil.copy2(img_path, agent_img_dir / img_path.name)
            
            # Parse step: 001_comment.png -> 1
            try:
                parts = img_path.name.split('_')
                step_str = parts[0]
                if step_str.isdigit():
                    step = int(step_str)
                    images_map[step] = img_path.name
            except Exception:
                pass
                
        # Process JSONL
        output_lines = []
        with open(jsonl_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    step = record.get("step")
                    
                    # Find matching image
                    image_file = images_map.get(step)
                    
                    if image_file:
                        image_url = f"/simulation/images/{agent_id}/{image_file}"
                        if "result" not in record:
                            record["result"] = {}
                        record["result"]["screenshot"] = image_url
                        
                        # Also top level
                        record["screenshot"] = image_url
                        
                    output_lines.append(json.dumps(record))
                except json.JSONDecodeError:
                    pass
        
        # Write jsonl
        target_jsonl = TARGET_DIR / f"{agent_id}.jsonl"
        with open(target_jsonl, 'w') as f:
            f.write('\n'.join(output_lines))
            
        agent_files.append(f"{agent_id}.jsonl")

    # Update index.json
    index_data = {
        "updated_at": datetime.now().isoformat(),
        "files": agent_files
    }
    with open(TARGET_DIR / "index.json", 'w') as f:
        json.dump(index_data, f, indent=2)
        
    print(f"Deployed {len(agent_files)} agent feeds.")

if __name__ == "__main__":
    main()
