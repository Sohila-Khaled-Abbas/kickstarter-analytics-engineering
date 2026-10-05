# How to Run the Kickstarter Downloader Script

Follow these steps to set up your environment, install the necessary dependencies, and run your asynchronous downloader script.

## Step 1: Verify Your Output Directory
Open `download_kickstarter_datasets.py` in your code editor and double-check the `OUTPUT_DIR` variable near the top of the file:
```python
OUTPUT_DIR = Path(
    r"D:\courses\Data Analysis 26-27\Projects\Kickstarter Projects\data"
)
```
Make sure this `D:\` drive path exists on your machine, or change it to a folder path that works for you (e.g., `C:\kickstarter_data`).

## Step 2: Install Required Python Packages
This script relies on a few powerful third-party libraries for asynchronous HTTP requests, HTML parsing, and progress bars. 

Open your terminal or command prompt (CMD/PowerShell) and run the following command:
```bash
pip install aiohttp beautifulsoup4 tqdm
```

## Step 3: Run the Script
Once the dependencies are installed, navigate to the folder where you saved your Python script using the `cd` command. For example:
```bash
cd "D:\courses\Data Analysis 26-27\Projects\Kickstarter Projects"
```

Then, execute the script:
```bash
python download_kickstarter_datasets.py
```

## Step 4: What to Expect While Running
1. **Scraping:** The script will first read the WebRobots page to find all available links.
2. **Filtering:** It will immediately filter them down to just the **latest scrape per year** (preferring CSVs).
3. **Downloading:** You will see a master progress bar (`tqdm`) at the bottom of your terminal showing the total gigabytes being downloaded. 
4. **Resilience:** Because you built this with chunking and resuming capabilities, **if your internet drops or you press `Ctrl+C`**, simply run the `python download_kickstarter_datasets.py` command again. It will pick up exactly where it left off without re-downloading existing chunks!