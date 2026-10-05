# Kickstarter Analytics Engineering Project

![Kickstarter Data](assets/Kickstarter%20Color%20Palette%20-%20color-hex.com.png)

## Overview
This project involves the automated extraction, consolidation, and advanced modeling of Kickstarter campaign data. By merging historical snapshots from Kaggle with continuous monthly crawls from WebRobots, this project builds a highly accurate, deduplicated, and performant analytical model in Power BI. 

**This repository utilizes Power BI Developer Mode (.pbip) to version control the semantic model (DAX) and report definitions as plain text.**

## Architecture
1. **Extraction (Python):** An asynchronous Python script (`aiohttp`) targets the WebRobots AWS S3 bucket. It intelligently identifies the latest data scrape per year, prefers CSV over JSON, and utilizes HTTP range requests to download gigabytes of data in parallel, fully optimized for network resilience.
2. **Harmonization (Power Query / M):** Kaggle datasets and WebRobots continuous crawls are appended.
3. **Deduplication (Power Query / M):** Because campaigns exist across multiple temporal scrapes, data is sorted by update timestamp descending and deduplicated by `project_id`, ensuring only the final resolution state (Successful, Failed, Canceled) is modeled.
4. **Modeling (Power BI):** A strictly enforced Star Schema optimized for the VertiPaq engine, version-controlled via Power BI Project (`.pbip`) format.

## Repository Structure
* `/src/`: Contains the asynchronous ETL Python scripts.
* `/docs/`: Playbooks, advanced BI guides, and documentation.
* `/data/`: (Ignored via git) Directory for raw Kaggle/WebRobots datasets and metadata.
* `/powerbi/`: Contains the `.pbip` semantic model and report definition files.

## Setup Instructions

### 1. Python Environment
Ensure you have Python 3.9+ installed.
```bash
# Clone the repo
git clone https://github.com/yourusername/kickstarter-analytics.git
cd kickstarter-analytics

# Install dependencies
pip install -r requirements.txt

# Run the extraction script
python src/download_kickstarter_datasets.py
```

### 2. Power BI Setup
1. Ensure your datasets are prepared in the local `data/` folder.
2. Open Power BI Desktop.
3. Open `powerbi/kickstarter_model.pbip`.
4. Refresh the data model to load your local `data/` source files into the VertiPaq engine.