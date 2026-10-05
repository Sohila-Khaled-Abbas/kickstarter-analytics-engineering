import os
import zipfile
import gzip
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# ============================================================
# CONFIGURATION
# ============================================================

# Point this to the data directory where your zip/gz files were downloaded
DATA_DIR = Path(r"D:\courses\Data Analysis 26-27\Projects\Kickstarter Projects\data")

# Where the unzipped files will go
EXTRACT_DIR = DATA_DIR / "extracted"

# Number of parallel extraction workers
MAX_WORKERS = 4 

# ============================================================
# EXTRACTION FUNCTIONS
# ============================================================

def extract_zip(file_path, output_folder):
    """Extracts a standard .zip file to the target output folder."""
    output_folder.mkdir(parents=True, exist_ok=True)
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(output_folder)
        return True, file_path.name, None
    except Exception as e:
        return False, file_path.name, str(e)

def extract_json_gz(file_path, output_folder):
    """Extracts a .json.gz file into a standard .json file."""
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Remove the '.gz' extension for the output file
    output_filename = file_path.name[:-3] 
    output_file_path = output_folder / output_filename
    
    try:
        with gzip.open(file_path, 'rb') as f_in:
            with open(output_file_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        return True, file_path.name, None
    except Exception as e:
        return False, file_path.name, str(e)

# ============================================================
# MAIN PROCESSING
# ============================================================

def process_file(file_path):
    """Determines the file type and routes it to the correct extractor."""
    # Determine the year from the parent folder (e.g., '2023')
    year = file_path.parent.name
    
    # Create a unique subfolder name based on the archive name 
    # to prevent CSV files from overwriting each other
    archive_name_no_ext = file_path.name.replace('.zip', '').replace('.json.gz', '')
    
    # Target path: data/extracted/2023/Kickstarter_2023-.../
    target_folder = EXTRACT_DIR / year / archive_name_no_ext
    
    # Check if already extracted by looking if the folder exists and has files
    if target_folder.exists() and any(target_folder.iterdir()):
        return True, file_path.name, "Already extracted"

    # Route based on extension
    if file_path.name.endswith('.zip'):
        return extract_zip(file_path, target_folder)
    elif file_path.name.endswith('.json.gz'):
        return extract_json_gz(file_path, target_folder)
    else:
        return False, file_path.name, "Unsupported file format"

def main():
    print("=" * 80)
    print("KICKSTARTER DATASET EXTRACTOR")
    print("=" * 80)
    print(f"Scanning directory: {DATA_DIR}")
    
    # Find all .zip and .json.gz files in the data directory (excluding the extraction folder itself)
    archives = []
    for ext in ['*.zip', '*.json.gz']:
        for path in DATA_DIR.rglob(ext):
            if "extracted" not in path.parts:
                archives.append(path)
                
    if not archives:
        print("No .zip or .json.gz archives found.")
        return

    print(f"Found {len(archives)} archives to extract.\n")
    
    success_count = 0
    fail_count = 0
    skipped_count = 0

    # Using ThreadPoolExecutor for concurrent extraction (faster disk I/O)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        futures = {executor.submit(process_file, path): path for path in archives}
        
        # Process with a progress bar
        for future in tqdm(as_completed(futures), total=len(archives), desc="Extracting"):
            success, filename, message = future.result()
            
            if success and message == "Already extracted":
                skipped_count += 1
            elif success:
                success_count += 1
            else:
                fail_count += 1
                print(f"\n[ERROR] Failed to extract {filename}: {message}")

    # Final Statistics
    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"Successfully extracted : {success_count}")
    print(f"Already extracted      : {skipped_count}")
    print(f"Failed                 : {fail_count}")
    print(f"\nExtracted files are located in:\n{EXTRACT_DIR}")

if __name__ == "__main__":
    main()