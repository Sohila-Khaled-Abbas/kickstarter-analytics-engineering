# Kickstarter Analytics: Advanced Power Query (M) Playbook

As an Analytics Engineer and Senior Power BI Developer, building a robust data pipeline directly inside Power BI requires mastering the Power Query Graphical User Interface (GUI), the underlying M language, and the VertiPaq engine's memory management.

Because we are dealing with three distinct source families with massive temporal overlaps (Kaggle snapshots vs. WebRobots continuous crawls), standard point-and-click transformations will not be enough. This guide walks you step-by-step through staging, harmonizing, deduplicating, and modeling your data.

                    KICKSTARTER ANALYTICS
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
 MasterKickstarter  Kickstarter Projects    WebRobots
  source family       source family       source family
        │                   │                   │
        ▼                   ▼                   ▼
   Historical          Historical           Recurring
   snapshot +          snapshots             crawls
 mapping tables 

---

## 🛠️ Pre-Requisite: Parameterize Your Data Source
*Senior Pro-Tip:* Hardcoding local file paths (`C:\Users\...`) is a bad practice. When you publish or share this `.pbip`, it will break.
1. In Power Query, click **Manage Parameters -> New Parameter**.
2. Name: `DataFolderPath`. Type: `Text`.
3. Current Value: `D:\courses\Data Analysis 26-27\Projects\Kickstarter Projects\data\`
*Use this parameter instead of hardcoding the path in your Folder and CSV connectors!*

---

## Phase 1: Data Ingestion & Staging (GUI + M Code)

Create a "Staging" query for each of the three families to load and pre-clean the raw data. **Do not load these directly to the report; right-click each and disable "Enable Load".**

### 1. Staging_Master & Auxiliary Tables (Historical Snapshot)

* **GUI Steps for Master:**
  1. Click **Get Data -> Text/CSV** and load `raw/master_kickstarter/MasterKickstarter.csv`. Name it `Staging_Master`.

* **Handling Mapping.csv (State Aggregations):**
  1. Load `Mapping.csv`. Name it `Dim_State_Metrics`.
  2. **CRITICAL:** This file contains pre-aggregated data (`Mean Campaign USD`, `Projects Per`, etc.). Do not merge this with campaign data. Keep it as a standalone lookup table.

* **Handling County.csv (Subregion Aggregations):**
  1. Load `County.csv`. Name it `Dim_County_Metrics`.
  2. **CRITICAL:** Just like the Mapping file, this contains pre-aggregated metrics (`TotalBackers`, `MeanUSD`, etc.). Do *not* merge this into `Staging_Master`. 

### 2. Staging_KaggleProjects (2016 & 2018 Snapshots)

This folder contains `ks-projects-201612.csv` and `ks-projects-201801.csv`. A campaign active in 2016 will *also* appear in the 2018 file, creating duplicates. 

* **GUI Steps:**
  1. Click **Get Data -> Folder**. Browse to `raw/kickstarter_projects/`.
  2. Click **Combine & Transform Data**. Power BI stacks them.
  3. Name the query `Staging_KaggleProjects`.
  4. **Data Quality Fix:** The Kaggle 2018 file contains columns like `pledged` (local currency) and `usd_pledged_real` (Fixer.io converted API currency). **Always keep the `_real` columns** for accurate cross-country analytics. Delete the raw local currency columns to save memory.

### 3. Staging_WebRobots (Recurring JSON/CSV Crawls)

This is the messy, massive recurring data with embedded JSON arrays.

* **GUI Steps:**
  1. Click **Get Data -> Folder**. Browse to `raw/webrobots/`.
  2. Click **Combine & Transform Data**. Name the query `Staging_WebRobots`.
  3. **Performance Tip:** Immediately remove all columns you don't need (e.g., `creator`, `photo`, `urls`) *before* doing any JSON parsing. This saves immense RAM.

* **The JSON Challenge (Advanced Editor):**
  Use this custom M code to parse the `category` and `location` columns safely:

  ```powerquery
  // Safely parse Category JSON
  ParsedCategory = Table.AddColumn(PreviousStep, "Category_Parsed", each try Json.Document([category]) otherwise null),
  ExpandedCategory = Table.ExpandRecordColumn(ParsedCategory, "Category_Parsed", {"name", "slug"}, {"subcategory_name", "category_slug"}),
  
  // Safely parse Location JSON (To match our County.csv geographical depth)
  ParsedLocation = Table.AddColumn(ExpandedCategory, "Location_Parsed", each try Json.Document([location]) otherwise null),
  ExpandedLocation = Table.ExpandRecordColumn(ParsedLocation, "Location_Parsed", {"country", "state", "displayable_name"}, {"country", "geo_state", "city_subregion"})
  ```

---

## Phase 2: Schema Harmonization

Before appending, the columns in all three staging queries must match *perfectly*. Power Query append is case-sensitive!

1. **Add Lineage Column:** Go to **Add Column -> Custom Column**. Name it `Source_Family`. Enter `"MasterKickstarter"`, `"KaggleProjects"`, or `"WebRobots"`.
2. **Standardize Naming:** 
   * Rename Kaggle's `usd_pledged_real` -> `pledged_usd`.
   * Rename Kaggle's `usd_goal_real` -> `goal_usd`.
   * Rename Kaggle's `main_category` -> `category_name`.
   * Rename WebRobots' `id` -> `project_id`.
3. **Strict Data Types:** Select all columns (`Ctrl+A`) and click **Detect Data Type**. Ensure `launched_at` is Date/Time, and financial columns are Fixed Decimal Number (Currency).

---

## Phase 3: Integration & Append

Now we stack the families into a single, massive table.

1. On the Home tab, click **Append Queries -> Append Queries as New**.
2. Select **Three or more tables**. Add all three Staging queries.
3. Name this new query `Fact_Campaigns_Raw`.

---

## Phase 4: Advanced Deduplication (`Table.Buffer`)

Power Query uses "Lazy Evaluation." If you just sort by date and click "Remove Duplicates," the Mashup Engine often ignores the sort order to save time, resulting in random, outdated records being kept. You *must* buffer the table in memory to force it to respect the sort order.

* **M Code (Advanced Editor):**
  Open the Advanced Editor for `Fact_Campaigns_Raw` and replace the final steps with this logic:

  ```powerquery
      // 1. Sort Descending by Date (Keep newest) and Source (Prefer WebRobots over Kaggle)
      SortedRows = Table.Sort(PreviousStepName,{{"launched_at", Order.Descending}, {"Source_Family", Order.Descending}}),
  
      // 2. Buffer the table in memory to FORCE the engine to respect the sort order.
      BufferedTable = Table.Buffer(SortedRows),
  
      // 3. Remove duplicates based on Project ID. Keeps the top (newest) row!
      Deduplicated = Table.Distinct(BufferedTable, {"project_id"})
  in
      Deduplicated
  ```

---

## Phase 5: Dimensional Modeling (Star Schema)

VertiPaq thrives on narrow Fact tables (numbers/dates) and distinct Dimension tables (text). 

### 1. Dimensions (Reference `Fact_Campaigns_Raw` to create these)
* **`Dim_Category`:** Keep `category_name`, `subcategory_name`. Remove Duplicates. Add Index `category_id`.
* **`Dim_Location`:** Keep `country`, `geo_state`, `city_subregion`. Remove Duplicates. Add Index `location_id`.

### 2. The Final Fact Table
1. Reference `Fact_Campaigns_Raw`. Name it `Fact_Campaigns`.
2. Merge with `Dim_Category` and `Dim_Location` to bring in `category_id` and `location_id`.
3. **CRITICAL:** Delete all heavy text columns (`category_name`, `country`, `name`, etc.) from the Fact table. Only keep IDs, Dates, and numeric metrics.

### 3. Build a Date Dimension (M-Code)
You need a proper Date table for time-intelligence DAX. Create a Blank Query and paste this standard script:
```powerquery
= List.Dates(#date(2009,1,1), Duration.Days(DateTime.Date(DateTime.LocalNow()) - #date(2009,1,1)), #duration(1,0,0,0))
// Convert to table, change type to Date, and extract Year, Month Name, Month Number, etc.
```
Name it `Dim_Date`.

---

## Phase 6: The Semantic Model View (Best Practices)

Click **Close & Apply**. In the Power BI Model View, build your Snowflake schema:

1. **Core Relationships:**
   * `Dim_Category[category_id]` -1:M-> `Fact_Campaigns[category_id]`
   * `Dim_Location[location_id]` -1:M-> `Fact_Campaigns[location_id]`
   * `Dim_Date[Date]` -1:M-> `Fact_Campaigns[launched_at]`
2. **Snowflake the Metrics:**
   * Link `Dim_State_Metrics[State]` -1:M-> `Dim_Location[geo_state]` 
   * Link `Dim_County_Metrics[subregion]` -1:M-> `Dim_Location[city_subregion]`
3. **UI / UX Polish:**
   * Select all `_id` columns (like `category_id`) across all tables. In the properties pane, turn on **Is Hidden**. End-users should filter by names, not ID numbers.
   * Format `pledged_usd` and `goal_usd` as Currency ($) with 0 decimal places.
   * Set `backers_count` summarization to Sum, and `project_id` summarization to "Count Distinct".