import os
import shutil
from pathlib import Path
from tqdm import tqdm

# ============================================================
# CONFIGURATION
# ============================================================
BASE_DIR = Path(r"D:\courses\Data Analysis 26-27\Projects\Kickstarter Projects\data")
EXTRACTED_DIR = BASE_DIR / "extracted"
RAW_WEBROBOTS_DIR = BASE_DIR / "raw" / "webrobots"

def flatten_and_copy():
    print("=" * 80)
    print("PREPARING RAW WEBROBOTS DATA FOR POWER BI")
    print("=" * 80)
    
    # Ensure the destination directory exists
    RAW_WEBROBOTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find all CSV and JSON files, strictly ignoring directories
    files_to_copy = []
    for ext in ['*.csv', '*.json']:
        found_paths = EXTRACTED_DIR.rglob(ext)
        # CRITICAL FIX: Ensure the path is a file, not a directory masquerading as a file
        files_to_copy.extend([p for p in found_paths if p.is_file()])
        
    if not files_to_copy:
        print(f"No valid CSV or JSON files found in {EXTRACTED_DIR}")
        return

    print(f"Found {len(files_to_copy)} files. Copying to {RAW_WEBROBOTS_DIR}...\n")
    
    success_count = 0
    skipped_count = 0
    fail_count = 0
    
    for file_path in tqdm(files_to_copy, desc="Copying Files"):
        # The path looks like: data/extracted/2014/Kickstarter_2014-12.../Kickstarter.csv
        parts = file_path.relative_to(EXTRACTED_DIR).parts
        
        if len(parts) >= 3:
            year = parts[0]
            scrape_id = parts[1]
            original_filename = parts[-1]
            safe_filename = f"{year}_{scrape_id}_{original_filename}"
        else:
            safe_filename = f"{file_path.parent.name}_{file_path.name}"
            
        destination_path = RAW_WEBROBOTS_DIR / safe_filename
        
        # Skip files that have already been copied
        if destination_path.exists() and destination_path.stat().st_size > 0:
            skipped_count += 1
            continue
            
        try:
            shutil.copy(file_path, destination_path)
            success_count += 1
        except Exception as e:
            print(f"\nError copying {file_path.name}: {e}")
            fail_count += 1
            
    print("\n" + "=" * 80)
    print("COPY COMPLETE")
    print("=" * 80)
    print(f"Successfully copied : {success_count} files")
    print(f"Already existed     : {skipped_count} files (Skipped)")
    print(f"Failed              : {fail_count} files")
    print(f"\nTarget Directory: {RAW_WEBROBOTS_DIR}")
    print("You are now ready to connect Power BI to this folder!")

if __name__ == "__main__":
    flatten_and_copy()