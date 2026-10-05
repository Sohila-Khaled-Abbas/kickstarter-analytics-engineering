import pandas as pd
import json
import glob
from pathlib import Path
from tqdm import tqdm
import os

# ============================================================
# CONFIGURATION
# ============================================================
BASE_DIR = Path(r"D:\courses\Data Analysis 26-27\Projects\Kickstarter Projects\data")
# The unzipped CSVs are now directly inside raw/webrobots
SOURCE_DIR = BASE_DIR / "raw" / "webrobots"

# Output one level up to avoid recursively reading the output file in future runs
OUTPUT_FILE = BASE_DIR / "raw" / "WebRobots_Enrichment_Master.csv"

def extract_json_field(json_string, field_name):
    """Safely extracts a field from a JSON string column."""
    if pd.isna(json_string):
        return None
    try:
        data = json.loads(json_string)
        return data.get(field_name)
    except (json.JSONDecodeError, TypeError):
        return None

def extract_parent_category(json_string):
    """Extracts the parent category from a slug (e.g., 'technology/web' -> 'technology')."""
    if pd.isna(json_string):
        return None
    try:
        data = json.loads(json_string)
        slug = data.get('slug', '')
        return slug.split('/')[0] if '/' in slug else slug
    except (json.JSONDecodeError, TypeError):
        return None

def prepare_webrobots_enrichment():
    print("=" * 80)
    print("WEBROBOTS ENRICHMENT DATA PREP")
    print("=" * 80)
    
    # 1. Find all CSV files in the raw/webrobots folders
    search_pattern = str(SOURCE_DIR / "**" / "*.csv")
    csv_files = glob.glob(search_pattern, recursive=True)
    
    # Sort files chronologically (assuming folder structure contains year/date)
    # This ensures that later scrapes overwrite earlier ones during deduplication
    csv_files.sort()
    
    if not csv_files:
        print("No CSV files found in the extracted directory.")
        return
        
    print(f"Found {len(csv_files)} files. Processing and resolving internal duplicates...\n")
    
    # Dictionary to hold the absolute latest state of each project ID
    # Using a dictionary is highly memory efficient for deduplication
    latest_projects = {}
    
    # Columns we actually care about for enriching Kaggle
    usecols = ['id', 'name', 'state', 'country', 'launched_at', 'deadline', 
               'goal', 'usd_pledged', 'backers_count', 'category', 'static_usd_rate']
               
    total_rows_scanned = 0
    
    for file_path in tqdm(csv_files, desc="Parsing Scrapes"):
        try:
            # Read file, ignoring columns we don't need
            df = pd.read_csv(file_path, usecols=lambda c: c in usecols, low_memory=False)
            
            if df.empty or 'id' not in df.columns:
                continue
                
            total_rows_scanned += len(df)
            
            # Convert to dictionary records and update the master dictionary
            # Because files are sorted chronologically, newer records overwrite older ones for the same 'id'
            records = df.to_dict('records')
            for row in records:
                if pd.notna(row.get('id')):
                    latest_projects[row['id']] = row
                    
        except Exception as e:
            print(f"\n[WARNING] Skipping {os.path.basename(file_path)} due to error: {e}")
            
    print(f"\nScanned {total_rows_scanned:,} total rows.")
    print(f"Distilled down to {len(latest_projects):,} unique campaigns.")
    
    if not latest_projects:
        print("No valid data found to export.")
        return
        
    print("\nFormatting columns to match Kaggle schema...")
    master_df = pd.DataFrame.from_dict(latest_projects, orient='index')
    
    # 2. JSON Parsing & Schema Harmonization
    if 'category' in master_df.columns:
        master_df['category_name'] = master_df['category'].apply(extract_parent_category)
        master_df['subcategory_name'] = master_df['category'].apply(lambda x: extract_json_field(x, 'name'))
    else:
        master_df['category_name'] = None
        master_df['subcategory_name'] = None
        
    # Unix Timestamp to Datetime
    if 'launched_at' in master_df.columns:
        master_df['launched_at'] = pd.to_datetime(master_df['launched_at'], unit='s', errors='coerce')
    if 'deadline' in master_df.columns:
        master_df['deadline_at'] = pd.to_datetime(master_df['deadline'], unit='s', errors='coerce')
        
    # Calculate real USD goal
    if 'goal' in master_df.columns and 'static_usd_rate' in master_df.columns:
        master_df['goal_usd'] = master_df['goal'] * master_df['static_usd_rate']
    else:
        master_df['goal_usd'] = None
        
    # Rename to match Kaggle
    master_df = master_df.rename(columns={
        'id': 'project_id',
        'usd_pledged': 'pledged_usd'
    })
    
    # Tag the source
    master_df['Source_Family'] = 'WebRobots_Enrichment'
    
    # Select final columns
    final_cols = ['project_id', 'name', 'state', 'category_name', 'subcategory_name', 
                  'country', 'launched_at', 'deadline_at', 'goal_usd', 'pledged_usd', 
                  'backers_count', 'Source_Family']
                  
    # Ensure columns exist to prevent KeyError
    for col in final_cols:
        if col not in master_df.columns:
            master_df[col] = None
            
    master_df = master_df[final_cols]
    
    # 3. Export
    print(f"Exporting enriched raw file to: {OUTPUT_FILE}")
    master_df.to_csv(OUTPUT_FILE, index=False)
    print("\nSUCCESS! You are ready to import this file into Power BI.")

if __name__ == "__main__":
    prepare_webrobots_enrichment()