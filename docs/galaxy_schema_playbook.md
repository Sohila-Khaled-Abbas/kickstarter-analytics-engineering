# Kickstarter Analytics Engineering: Galaxy Schema Playbook

> **Architectural Objective:** Build an enterprise-grade analytics pipeline using a **Galaxy Schema (Fact Constellation)**. Instead of flattening recurring WebRobots crawls into a single deduplicated row (which destroys historical time-series data), we will build multiple Fact tables sharing conformed dimensions. This allows for rich, temporal analysis of campaign funding trajectories alongside canonical portfolio metrics.

---

## 1. The Galaxy Schema Architecture

The core of this model separates the **static identity of a project** from its **changing state over time**, while isolating **geographic aggregates** to prevent granularity explosions.

```mermaid
graph TD
    subgraph 🌌 Conformed Dimensions
        D[Dim_Date]
        C[Dim_Category]
        L[Dim_Location]
        Curr[Dim_Currency]
        S[Dim_Status]
        P[Dim_Project]
    end

    subgraph 📊 Fact Constellation
        F1[[Fact_Campaign<br/>(1 row / Project)]]
        F2[[Fact_CampaignSnapshot<br/>(1 row / Project x Month)]]
        F3[[Fact_CityMetrics<br/>(1 row / City)]]
        F4[[Fact_StateMetrics<br/>(1 row / State)]]
        F5[[Fact_CountyMetrics<br/>(1 row / County)]]
    end

    %% Fact Campaign Links
    D -->|LaunchDateKey| F1
    C --> F1
    L --> F1
    Curr --> F1
    S --> F1
    P --> F1

    %% Fact Snapshot Links
    D -->|SnapshotDateKey| F2
    C --> F2
    L --> F2
    Curr --> F2
    S --> F2
    P --> F2

    %% Geo Metrics Links
    L --> F3
    L --> F4
    L --> F5
```

### Table Grains (The Golden Rule)
*Never mix these grains in a single table.*

| Table | Grain |
| :--- | :--- |
| **Fact_Campaign** | One row per unique Kickstarter project (The canonical record). |
| **Fact_CampaignSnapshot** | One row per project per WebRobots snapshot date (Time-series). |
| **Fact_CityMetrics** | One row per city per defined period/source. |
| **Fact_StateMetrics** | One row per state per defined period/source. |
| **Fact_CountyMetrics** | One row per county per defined period/source. |

---

## 2. Power Query Workspace Architecture

To maintain a professional, senior-level workspace, strictly use this 7-tier Grouping structure in the Power Query Editor:

```text
00 Parameters
 ├── pDataFolder
 ├── pDefaultCurrency

01 Sources (Raw extraction only)
 ├── Src_Kaggle_2016
 ├── Src_Kaggle_2018
 ├── Src_MasterKickstarter
 ├── Src_WebRobots
 ├── Src_Mapping
 └── Src_County

02 Staging (Cleaning, encoding, parsing)
 ├── Stg_Kaggle_2016
 ├── Stg_Kaggle_2018
 └── ...

03 Conformed (Appending & Deduplication)
 ├── Conformed_Project
 └── Conformed_Location...

04 Dimensions (Enable Load)
 ├── Dim_Project
 └── Dim_Date...

05 Facts (Enable Load)
 ├── Fact_Campaign
 └── Fact_CampaignSnapshot...

99 QA (Audits & Checks)
 ├── QA_DuplicateProjects
 └── QA_NullKeys...
```
*(Only folders `04 Dimensions` and `05 Facts` should have tables with **"Enable Load"** checked).*

---

## 3. Phase 1: Staging the Sources

### Source 1: Kaggle 2018 (The Base Schema)
1. **Rename Columns:** `ID` -> `ProjectID`, `name` -> `ProjectName`, `category` -> `Subcategory`, `main_category` -> `Category`, `usd_pledged_real` -> `PledgedUSD`, `usd_goal_real` -> `GoalUSD`.
2. **Clean Text:** Apply `Text.Trim()` and `Text.Clean()` to all text columns. Convert Status to lowercase.
3. **Data Types:** Ensure `ProjectID` is Int64. Dates are Date/Time. Currencies are Decimal Number.

### Source 2: Kaggle 2016 (The Encoding Fix)
The 2016 file has malformed columns and encoding issues.
1. **Encoding:** When reading the CSV, set the Origin to `Windows-1252`.
2. **Clean Garbage:** Delete `Unnamed: 13`, `Unnamed: 14`, etc.
3. **GoalUSD Logic:** This file lacks `usd_goal_real`. Do *not* fake it. 
   * Custom Column: `if [currency] = "USD" then [goal] else null`.

### Source 3: MasterKickstarter (Geo-Enrichment)
This file contains ~57 columns including geographic metrics.
1. **Normalize Names:** California, CALIFORNIA, california -> `Text.Proper(Text.Trim([State]))`.
2. **Split the Grain:** Keep Campaign-level data (`ProjectID`, `Status`) in staging. Move aggregate columns (`City_Pop`, `Mean_Backers`) to a separate `Stg_CityMetrics` query. Do not merge them into campaign facts!

### Source 4: WebRobots (The Snapshot Engine)
WebRobots provides monthly historical snapshots.
1. **Extract Snapshot Date:** Parse the filename to derive the snapshot date (e.g., `Kickstarter_2023-05-18.csv` -> `2023-05-18`). This is crucial.
2. **Unix Timestamps:** Convert `launched_at`, `deadline`, etc., using: `#datetime(1970,1,1,0,0,0) + #duration(0,0,0,[launched_at])`
3. **Parse JSON:** Expand the `category` and `location` JSON columns. Extract `category.name`, `location.country`, `location.state`. *Do not keep the raw JSON blobs.*

---

## 4. Phase 2: Building Dimensions

Reference your `03 Conformed` tables to build distinct dimensions. Add an `Index Column` (starting from 1) to serve as your Surrogate Key (e.g., `ProjectKey`, `CategoryKey`).

*   **`Dim_Project`**: `ProjectKey`, `ProjectID`, `ProjectName`, `Slug`, `Blurb`, `ProjectURL`, `LaunchDate`, `DeadlineDate`. *(Do NOT include Pledged/Backers here).*
*   **`Dim_Category`**: `CategoryKey`, `MainCategory`, `Subcategory`.
*   **`Dim_Location`**: `LocationKey`, `CountryCode`, `CountryName`, `State`, `City`, `Latitude`, `Longitude`.
*   **`Dim_Currency`**: `CurrencyKey`, `CurrencyCode`, `CurrencySymbol`.
*   **`Dim_Status`**: `StatusKey`, `Status` (e.g., successful, failed), `OutcomeGroup`, `IsCompleted` (1/0), `IsSuccessful` (1/0).

### Building Dim_Date (DAX)
Create this table using DAX in the Data view:
```dax
Dim_Date = 
ADDCOLUMNS(
    CALENDAR(DATE(2009,1,1), DATE(2026,12,31)),
    "DateKey", VALUE(FORMAT([Date], "YYYYMMDD")),
    "Year", YEAR([Date]),
    "MonthNumber", MONTH([Date]),
    "MonthName", FORMAT([Date], "MMMM"),
    "YearMonth", FORMAT([Date], "YYYY-MM"),
    "Quarter", "Q" & FORMAT([Date], "Q")
)
```

---

## 5. Phase 3: Building the Fact Constellation

### Fact_Campaign (The Static Master)
*   **Grain:** 1 row per unique ProjectID.
*   **Source Priority:** Deduplicate based on ProjectID. Prioritize Kaggle 2018/Master for base metadata.
*   **Keep Keys & Measures Only:** `ProjectKey`, `CategoryKey`, `LocationKey`, `CurrencyKey`, `StatusKey`, `LaunchDateKey`, `GoalUSD`, `PledgedUSD`, `BackerCount`.
*   **Remove:** All descriptive text (Names, Cities, Categories).

### Fact_CampaignSnapshot (The WebRobots Time-Series)
*   **Grain:** 1 row per ProjectID + SnapshotDate.
*   **Logic:** Do *not* deduplicate just by ProjectID. Group by `ProjectID` AND `SnapshotDate`. 
*   **Keep Keys & Measures Only:** `ProjectKey`, `SnapshotDateKey`, `CategoryKey`, `StatusKey`, `PledgedUSD`, `BackerCount`, `StaffPickFlag`.

### Fact_StateMetrics / Fact_CountyMetrics
*   **Source:** `Mapping.csv` and `County.csv`.
*   **Logic:** Link these directly to `Dim_Location` via `LocationKey`. They contain `MeanUSD`, `MedianBackers`. They are independent facts.

---

## 6. Semantic Model & Relationships

1.  **Cardinality:** ALWAYS **1-to-Many (1:*)** from Dimension to Fact. Single cross-filter direction. 
    *   `Dim_Category[CategoryKey]` 1:* `Fact_Campaign[CategoryKey]`
    *   `Dim_Project[ProjectKey]` 1:* `Fact_CampaignSnapshot[ProjectKey]`
2.  **Date Roles:** 
    *   Link `Dim_Date[DateKey]` to `Fact_Campaign[LaunchDateKey]` (Active).
    *   Link `Dim_Date[DateKey]` to `Fact_Campaign[DeadlineDateKey]` (Inactive). Use `USERELATIONSHIP()` in DAX when analyzing deadlines.
3.  **UI Polish:** Right-click every `*Key` column in your Fact tables and select **Hide in report view**. End users should only filter using Dimensions!

---

## 7. Advanced DAX Measures

Create a dedicated `Measures` table.

### Core Portfolio Analytics
```dax
Total Projects = DISTINCTCOUNT(Fact_Campaign[ProjectKey])

Total Pledged USD = SUM(Fact_Campaign[PledgedUSD])

Successful Projects = 
CALCULATE(
    [Total Projects],
    Dim_Status[IsSuccessful] = 1
)

Success Rate = DIVIDE([Successful Projects], CALCULATE([Total Projects], Dim_Status[IsCompleted] = 1), 0)

Funding Ratio = DIVIDE([Total Pledged USD], SUM(Fact_Campaign[GoalUSD]), 0)
```

### Temporal Snapshot Analytics (The Power of WebRobots)
```dax
Snapshot Pledged USD = SUM(Fact_CampaignSnapshot[PledgedUSD])

Previous Snapshot Pledged = 
CALCULATE(
    [Snapshot Pledged USD],
    DATEADD(Dim_Date[Date], -1, MONTH)
)

Pledged Growth = [Snapshot Pledged USD] - [Previous Snapshot Pledged]

Pledged Growth % = DIVIDE([Pledged Growth], [Previous Snapshot Pledged], 0)
```

---

## 8. Phase 4: QA Auditing

Create these reference queries in the `99 QA` folder (Disable Load):

1.  **`QA_DuplicateProjects`:** Reference `Fact_Campaign`. Group by `ProjectKey`, count rows, filter for `> 1`. (Must be empty).
2.  **`QA_DuplicateSnapshots`:** Reference `Fact_CampaignSnapshot`. Group by `ProjectKey` AND `SnapshotDateKey`, count rows, filter for `> 1`. (Must be empty).
3.  **`QA_OrphanKeys`:** Reference Facts. Filter `LocationKey` or `CategoryKey` for `null`. 
4.  **`QA_ValueChecks`:** Filter `Fact_Campaign` for `DurationDays < 0` or `GoalUSD < 0`. Investigate anomalies without blindly deleting them.