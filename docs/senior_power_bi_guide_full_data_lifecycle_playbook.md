# Kickstarter Analytics Engineering: 100% Power BI Playbook

> **Project Objective:** Build an enterprise-grade analytics pipeline entirely within Power BI. We will bypass external Python/SQL tools and rely strictly on Advanced Power Query (M) and DAX. We will manually ingest specific raw files (avoiding risky folder combiners), harmonize schemas, perform deterministic deduplication, and construct a highly optimized VertiPaq Star Schema using a strict 7-tier architecture.

---

## The 7-Tier Power Query Architecture

To maintain a professional, senior-level workspace, right-click the empty space in your Power Query Editor's "Queries" pane and create the following **New Groups**:

1. `00 Parameters`
2. `01 Sources`
3. `02 Staging`
4. `03 Conformed`
5. `04 Dimensions`
6. `05 Facts`
7. `99 QA`

**CRITICAL RULE:** Every query in groups `01` through `03` MUST have **"Enable Load" unchecked**. Only the final dimensions and facts in groups `04` and `05` will load into the Data Model.

---

## 00 Parameters

Hardcoding file paths means your entire dashboard breaks if you move the project folder. 

1. Right-click the `00 Parameters` group -> **New Parameter**.
2. **Name:** `DataFolderPath`
3. **Type:** Text
4. **Current Value:** `D:\courses\Data Analysis 26-27\Projects\Kickstarter Projects\data\raw\` *(Update this to wherever your CSV files live).*

---

## 01 Sources (Raw Ingestion)

**Do NOT use the "Folder" connector.** The folder connector uses hidden helper queries and arbitrary sample files that break easily. Instead, we will point directly to our explicit files.

For each of the files below, go to **New Source -> Text/CSV**, browse to the file, and click OK. Then, open the Advanced Editor and replace the hardcoded path with `DataFolderPath & "filename.csv"`. Move all these queries into the `01 Sources` group.

1. **`Src_Kaggle_2016`**: Points to `ks-projects-201612_2.csv`
2. **`Src_Kaggle_2018`**: Points to `ks-projects-201801_2.csv`
3. **`Src_Master`**: Points to `MasterKickstarter.csv`
4. **`Src_WebRobots_Latest`**: Points to your specific extracted WebRobots CSV (e.g., `Kickstarter_2023.csv`). *Repeat this step for each specific year's CSV you wish to include.*
5. **`Src_Mapping`**: Points to `Mapping.csv` (State Aggregates)
6. **`Src_County`**: Points to `County.csv` (County Aggregates)

*Rule: Make absolutely zero transformations in this folder. This is a pure read of the raw data.*

---

## 02 Staging (Harmonization)

Here, we map the varying column names from our different sources into one unified canonical schema. Right-click each query in `01 Sources` (except the geography aggregates) and select **Reference**. Move these new queries to `02 Staging`.

### Stg_Kaggle_2016 & Stg_Kaggle_2018
1. Standardize columns: rename `ID` -> `project_id`, `name` -> `project_name`, `main_category` -> `category_name`, `category` -> `subcategory_name`.
2. Map USD columns: For 2018, rename `usd_goal_real` -> `goal_usd` and `usd_pledged_real` -> `pledged_usd`. For 2016, rename `usd pledged` to `pledged_usd`.
3. Add Custom Column: `Source_System` = `"Kaggle_2018"` (or 2016).
4. Add Custom Column: `Snapshot_Date` = `#date(2018, 1, 1)` (Set a static date representing when the dataset was published).
5. Ensure Datatypes are perfect (Text for IDs, DateTime for launched/deadline, Currency/Decimal for money).

### Stg_Master
1. Rename columns to match the standard exactly. 
2. Add `Source_System` = `"MasterKickstarter"`.
3. Add `Snapshot_Date` = `#date(2017, 12, 31)`.

### Stg_WebRobots
1. If WebRobots has nested JSON categories, parse them now (`Transform -> Parse -> JSON`, then expand).
2. Rename columns to match your canonical standard.
3. Add `Source_System` = `"WebRobots_2023"` (or respective year).
4. Extract or define the `Snapshot_Date`.

*Remove all columns from all Staging queries that do not match the canonical standard.*

---

## 03 Conformed (The Grand Append & Deduplication)

This is where we combine everything and resolve temporal overlaps natively in M-Code.

### 1. The Append
1. Click **Append Queries as New**.
2. Select all your Staging queries (`Stg_Kaggle_2016`, `Stg_Kaggle_2018`, `Stg_Master`, `Stg_WebRobots`).
3. Name this new query `Project_Universe_Raw` and put it in the `03 Conformed` group.

### 2. Deterministic Deduplication (Advanced Editor)
A project might exist in 2016 (Live), 2018 (Failed), and WebRobots (Successful). We only want the *latest* state. Instead of risky `Table.Buffer` sorts, we will use a memory-efficient grouping pattern. Open the Advanced Editor for `Project_Universe_Raw` and add this logic to the end:

```powerquery
    // Assume "AppendedSources" is your append step
    
    // Group by Project ID to find the absolute latest snapshot date for each campaign
    GroupedRows = Table.Group(AppendedSources, {"project_id"}, {
        // Table.Max looks at all rows for a given project_id and returns the entire record (row) with the newest date
        {"LatestRecord", each Table.Max(_, "Snapshot_Date"), type record}
    }),
    
    // Expand that winning record back into standard columns
    ExpandedRecord = Table.ExpandRecordColumn(GroupedRows, "LatestRecord", 
        {"project_name", "category_name", "subcategory_name", "country", "launched_at", "deadline_at", "goal_usd", "pledged_usd", "backer_count", "project_state", "Source_System", "Snapshot_Date"}
    )
in
    ExpandedRecord
```

*You now have a mathematically perfect, deduplicated universe of Kickstarter campaigns.*

---

## 04 Dimensions

We will now build a Star Schema optimized for the VertiPaq engine. Right-click `Project_Universe_Raw` and select **Reference** to create your dimensions. Move them to `04 Dimensions`. **Check "Enable Load"** for all of these.

*   **`Dim_Project`**: Keep `project_id`, `project_name`, `launched_at`, `deadline_at`. Remove duplicates based on `project_id`. (This acts as a degenerate dimension for text heavy data).
*   **`Dim_Category`**: Keep `category_name`, `subcategory_name`. Remove duplicates. Add an Index Column starting from 1 named `category_id`. 
*   **`Dim_Location`**: Keep `country`. Remove duplicates. Add an Index Column named `location_id`.

**The Snowflake Geographic Aggregates:**
Reference `Src_Mapping` and `Src_County`. Move them to `04 Dimensions`. Name them `Dim_State_Metrics` and `Dim_County_Metrics`. Ensure column names are clean and types are numerical where appropriate. Do *not* merge these into campaign-level tables!

---

## 05 Facts

This is the core numerical table.
1. Right-click `Project_Universe_Raw` -> **Reference**. Name it `Fact_Campaigns`. Move to `05 Facts`.
2. **Merge** with `Dim_Category` (matching on category text). Expand to extract `category_id`.
3. **Merge** with `Dim_Location` (matching on country). Expand to extract `location_id`.
4. **CRITICAL:** Delete all text columns (`category_name`, `country`, `project_name`) from the Fact table. 
5. Keep only: `project_id`, `category_id`, `location_id`, `goal_usd`, `pledged_usd`, `backer_count`, `project_state`.
6. **Check "Enable Load"**.

---

## 99 QA

Create reference queries to audit your data. (Keep "Enable Load" unchecked; these are for developer verification).
*   **`QA_Duplicate_Check`**: Reference `Fact_Campaigns`. Group by `project_id` and count rows. Filter for counts > 1. This query should always be *Empty*.
*   **`QA_Missing_Keys`**: Reference `Fact_Campaigns`. Filter `category_id` or `location_id` for `null`. This reveals if your joins failed due to whitespace/casing issues.

---

## The Semantic Model (DAX & Layout)

Click **Close & Apply**. Power BI will read the explicit files, standardize them, execute the deterministic grouping deduplication, assign foreign keys, and load the narrow tables into memory.

### 1. Model View (Relationships)
*   `Dim_Category[category_id]` -1:M-> `Fact_Campaigns[category_id]`
*   `Dim_Location[location_id]` -1:M-> `Fact_Campaigns[location_id]`
*   `Dim_Project[project_id]` -1:1-> `Fact_Campaigns[project_id]`

**Snowflake the Aggregates:**
*   Link `Dim_State_Metrics[State]` -> `Dim_Location[State]` (If State exists).
*   Link `Dim_County_Metrics[subregion]` -> `Dim_Location[County/Subregion]`.

### 2. Core DAX Measures
Create a dedicated Measure Table.

```dax
Total Projects = DISTINCTCOUNT(Fact_Campaigns[project_id])

Total Pledged (USD) = SUM(Fact_Campaigns[pledged_usd])

Successful Projects = 
CALCULATE(
    [Total Projects],
    Fact_Campaigns[project_state] = "successful"
)

Success Rate = DIVIDE([Successful Projects], [Total Projects], 0)

Avg Pledged per Backer = DIVIDE([Total Pledged (USD)], SUM(Fact_Campaigns[backer_count]), 0)
```

### 3. UI/UX Polish
*   Right-click every `_id` column across all tables and select **Hide in report view**.
*   Save your project as a `.pbip` to lock in this immaculate architecture for version control!