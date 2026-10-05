# Kickstarter Analytics Engineering Playbook

As an Analytics Engineer, your goal is to transform raw, fragmented data from multiple sources (Kaggle snapshots + WebRobots continuous crawls) into a clean, unified, and performant analytical model in Power BI. 

This playbook covers three phases: updating your extraction script, handling deduplication, and building the Power BI model.

---

## Phase 1: Script Modification (Strictly Latest-Per-Year)

Your current `download_kickstarter_datasets.py` handles the parallel downloading and CSV/JSON fallback beautifully. However, it currently downloads *every* scrape available. To enforce the **latest-per-year** rule, we need to modify the `select_best_datasets` function.

Replace the existing `select_best_datasets` function in your script with this updated version:

```python
# ============================================================
# CHOOSE ONE FORMAT PER YEAR (LATEST SCRAPE)
# ============================================================

def select_best_datasets(all_datasets):
    """
    For every YEAR:
        1. Find the latest scrape_id (closest to Dec 31st).
        2. Prefer CSV for that scrape.
        3. If CSV doesn't exist, use JSON.
    """
    by_year = {}

    # Group datasets by year
    for dataset in all_datasets:
        year = dataset["year"]
        if year not in by_year:
            by_year[year] = []
        by_year[year].append(dataset)

    selected = []

    for year, versions in by_year.items():
        # 1. Identify the most recent scrape for this specific year
        latest_scrape_id = max(versions, key=lambda d: d["scrape_id"])["scrape_id"]
        
        # Filter down to only files belonging to this latest scrape
        latest_files = [d for d in versions if d["scrape_id"] == latest_scrape_id]

        csv_versions = [d for d in latest_files if d["format"] == "CSV"]
        json_versions = [d for d in latest_files if d["format"] == "JSON"]

        # 2 & 3. CSV has priority, otherwise fallback to JSON
        if csv_versions:
            selected.append(csv_versions[0])
        elif json_versions:
            selected.append(json_versions[0])

    # Sort final list by year descending
    selected.sort(key=lambda d: d["year"], reverse=True)

    return selected
```

---

## Phase 2: Understanding the Data & Deduplication Strategy

The core challenge of this project is overlapping data. 
*   **Kaggle Datasets:** These are usually historical snapshots (e.g., all data up to 2018).
*   **WebRobots:** These are monthly crawls. Even with our "latest per year" script, a campaign launched in Nov 2017 and ending in Jan 2018 will exist in the 2017 Kaggle data, the 2017 WebRobots file, *and* the 2018 WebRobots file.

### The Deduplication Golden Rule
Every Kickstarter project has a unique **Project ID**. Because a campaign's state changes over time (`live` -> `successful` or `failed`), you *always* want to keep the record with the most recent state. 

**Logic for Power BI / Data Prep:**
1. Union/Append all datasets together.
2. Sort the data by `updated_at` (or `state_changed_at`) in **Descending** order.
3. Remove Duplicates based entirely on the **Project ID**. This ensures the engine keeps the first row it encounters, which (because of our sorting) is the most recent update of that campaign.

---

## Phase 3: Power BI Integration & Modeling

Here is how you bring this together in Power BI using Power Query (M) and Data Modeling concepts.

### Step 1: Ingestion (Power Query)
1. **Load Kaggle Data:** Use `Get Data -> Text/CSV` to load your Kaggle files. Name this query `Staging_Kaggle`.
2. **Load WebRobots Data:** Use `Get Data -> Folder` and point it to `D:\courses\Data Analysis 26-27\Projects\Kickstarter Projects\data`. 
    * Filter the extension to `.zip` or `.csv`.
    * Click "Combine & Transform".
    * Power BI will automatically unzip the WebRobots CSVs and stack them. Name this query `Staging_WebRobots`.
3. *(Optional)* If you had to download JSON fallbacks, you will need to load them separately via `Get Data -> Folder` filtering for `.json.gz`, expand the records, and append them to `Staging_WebRobots`.

### Step 2: Harmonization & Append
Kaggle and WebRobots datasets might have slightly different column names (e.g., `id` vs `project_id`, or `usd_pledged` vs `pledged`). 
1. In Power Query, rename the columns in `Staging_Kaggle` and `Staging_WebRobots` so they match perfectly.
2. Go to `Home -> Append Queries as New`.
3. Append `Staging_Kaggle` and `Staging_WebRobots`. Name this new query `Fact_Campaigns_Raw`.

### Step 3: Deduplication in Power Query
On your `Fact_Campaigns_Raw` query:
1. Ensure you have a datetime column representing when the data was scraped or last updated.
2. Sort that column **Descending**.
3. Select your unique ID column (`id` or `project_id`).
4. Right-click the column header -> **Remove Duplicates**. 
5. *(Crucial)* Right-click your staging queries (`Staging_Kaggle`, `Staging_WebRobots`) and **uncheck "Enable Load"**. You only want the final appended, deduplicated table to load into your Power BI model to save memory.

### Step 4: Star Schema Design
To be a true Analytics Engineer, do not leave everything in one giant flat table. Break `Fact_Campaigns_Raw` into a Star Schema.

**1. Fact Table: `Fact_Campaigns`**
*   Contains metrics: `project_id`, `goal_usd`, `pledged_usd`, `backers_count`, `category_id`, `creator_id`, `launched_date`, `deadline_date`, `state`.

**2. Dimension Tables (Create these by referencing your Fact table and removing duplicates):**
*   **`Dim_Category`:** `category_id`, `category_name`, `parent_category`, `slug`.
*   **`Dim_Creator`:** `creator_id`, `creator_name`.
*   **`Dim_Location`:** `location_id`, `country`, `state`, `city`.
*   **`Dim_Date`:** Create a standard Calendar table in DAX (using `CALENDARAUTO()`) and link it to your `launched_date` and `deadline_date`.

### Step 5: DAX Quick Wins
Once modeled, you can easily create these key measures:
*   `Success Rate = DIVIDE(CALCULATE(COUNT(Fact_Campaigns[project_id]), Fact_Campaigns[state] == "successful"), COUNT(Fact_Campaigns[project_id]))`
*   `Avg Pledged per Backer = DIVIDE(SUM(Fact_Campaigns[pledged_usd]), SUM(Fact_Campaigns[backers_count]))`

By following this architecture, you guarantee that your dashboard will only reflect the final historical outcome of every single Kickstarter project, regardless of how many times it was scraped by WebRobots or Kaggle.