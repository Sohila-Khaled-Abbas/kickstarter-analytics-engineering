import os
import pandas as pd
from pathlib import Path
from tqdm import tqdm

# ============================================================
# CONFIGURATION
# ============================================================
BASE_DIR = Path(r"D:\courses\Data Analysis 26-27\Projects\Kickstarter Projects\data")
RAW_DIR = BASE_DIR / "raw"
METADATA_DIR = BASE_DIR / "metadata"

# Define the source families based on your architecture
SOURCE_FAMILIES = {
    "MasterKickstarter": RAW_DIR / "master_kickstarter",
    "Kickstarter Projects": RAW_DIR / "kickstarter_projects",
    "WebRobots": RAW_DIR / "webrobots"
}

def get_row_count(file_path):
    """Fastest way to count rows in massive CSV files without eating RAM."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f) - 1 # Subtract 1 for header
    except Exception:
        return -1

def generate_metadata():
    print("=" * 80)
    print("KICKSTARTER DATASET METADATA GENERATOR")
    print("=" * 80)
    
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    
    manifest_data = []
    schema_data = []
    
    # Collect all CSV files first
    files_to_process = []
    for family_name, folder_path in SOURCE_FAMILIES.items():
        if folder_path.exists():
            for file_path in folder_path.rglob("*.csv"):
                files_to_process.append((family_name, file_path))
        else:
            print(f"[WARNING] Source folder not found: {folder_path}")

    if not files_to_process:
        print("No CSV files found in the raw directories.")
        return

    print(f"Found {len(files_to_process)} datasets. Profiling metadata...\n")
    
    # Process each file with a progress bar
    for family_name, file_path in tqdm(files_to_process, desc="Scanning Files"):
        file_size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
        row_count = get_row_count(file_path)
        
        try:
            # Read just the first row to get the schema/datatypes instantly
            df_sample = pd.read_csv(file_path, nrows=0, low_memory=False)
            col_count = len(df_sample.columns)
            
            manifest_data.append({
                "Source_Family": family_name,
                "File_Name": file_path.name,
                "Relative_Path": str(file_path.relative_to(BASE_DIR)),
                "Size_MB": file_size_mb,
                "Row_Count": row_count,
                "Column_Count": col_count
            })
            
            for idx, col_name in enumerate(df_sample.columns):
                schema_data.append({
                    "Source_Family": family_name,
                    "File_Name": file_path.name,
                    "Column_Index": idx + 1,
                    "Column_Name": col_name,
                })
                
        except Exception as e:
            print(f"\n[ERROR] Failed to read schema for {file_path.name}: {e}")
            manifest_data.append({
                "Source_Family": family_name,
                "File_Name": file_path.name,
                "Relative_Path": str(file_path.relative_to(BASE_DIR)),
                "Size_MB": file_size_mb,
                "Row_Count": row_count,
                "Column_Count": "ERROR"
            })

    # ============================================================
    # EXPORT METADATA TO CSV
    # ============================================================
    print("\n" + "=" * 80)
    print("EXPORTING METADATA")
    print("=" * 80)
    
    manifest_df = pd.DataFrame(manifest_data)
    manifest_path = METADATA_DIR / "dataset_manifest.csv"
    manifest_df.to_csv(manifest_path, index=False)
    print(f"-> Manifest saved to: {manifest_path}")
    
    schema_df = pd.DataFrame(schema_data)
    schema_path = METADATA_DIR / "schema_registry.csv"
    schema_df.to_csv(schema_path, index=False)
    print(f"-> Schema Registry saved to: {schema_path}")
    
    total_rows = manifest_df['Row_Count'].sum()
    total_size = manifest_df['Size_MB'].sum()
    
    print("\n[PROJECT SUMMARY]")
    print(f"Total Datasets Processed: {len(manifest_df)}")
    print(f"Total Raw Rows: {total_rows:,}")
    print(f"Total Data Size: {total_size:,.2f} MB")
    print("You can now load schema_registry.csv into Power BI to help map your columns!")

if __name__ == "__main__":
    generate_metadata()