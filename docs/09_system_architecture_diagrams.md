# 09 — System Architecture & Data Engineering Diagrams

## Visual Architecture Blueprint: Data Engineering & Power BI Modeling

This document provides a comprehensive visual and technical breakdown of the **Kickstarter Analytics Engineering Platform**. Designed from an enterprise Data Engineering mindset, these diagrams illustrate how raw, fragmented web scrapes and historical snapshots are transformed into a governed, scalable Power BI semantic model.

---

## 1. End-to-End Medallion Lakehouse Pipeline Architecture

The platform applies the **Medallion Architecture (Bronze → Silver → Gold)** to decouple raw data ingestion from analytical consumption:

![Medallion Pipeline Architecture](../assets/diagrams/medallion_pipeline_architecture.png)

### Pipeline Flow Breakdown:

```mermaid
flowchart TD
    subgraph S1["1. Raw Ingestion & Source Assets"]
        W1["WebRobots Recurring Crawls<br/>361 Files (2014–2026)<br/>348k Master Records"]
        K1["Kaggle Snapshots<br/>2018 (378k) & 2016 (323k)<br/>Windows-1252 & UTF-8"]
        M1["MasterKickstarter.csv<br/>167k Records · 57 Cols<br/>Geospatial & Demographics"]
        B1["Regional Benchmarks<br/>County.csv (966 Counties)<br/>Mapping.csv (50 States)"]
    end

    subgraph S2["2. Bronze Staging Layer (Load Disabled)"]
        Stg1["Stg_Kaggle_2016<br/>Strip phantom columns, fix encoding"]
        Stg2["Stg_Kaggle_2018<br/>Fixer.io USD real conversions"]
        Stg3["Stg_MasterKickstarter<br/>Unix epoch to DateTime, type casts"]
        Stg4["Stg_WebRobots<br/>JSON parsing, slug extraction"]
        Stg5["Stg_County & Stg_Mapping<br/>Standardize benchmark metrics"]
    end

    subgraph S3["3. Silver Conformed Layer (Load Disabled)"]
        Union["Conformed_Campaign_AllSources<br/>1.2M+ Harmonized Records"]
        Dedup["Deterministic Deduplication Engine<br/>Table.Buffer + Recency Sorting"]
        Keys["Surrogate Key Generator<br/>Table.AddIndexColumn(1, 1, Int64)"]
        Dims["Entity Extraction<br/>Project, Category, Location, Currency, Status"]
    end

    subgraph S4["4. Gold Semantic Model (Enable Load = True)"]
        D_All["6 Conformed Dimensions<br/>Dim_Project, Dim_Category, Dim_Location<br/>Dim_Currency, Dim_Status, Dim_Date (M)"]
        F1["Fact_Campaign<br/>1 row / unique project (Canonical)"]
        F2["Fact_CampaignSnapshot<br/>1 row / project / scrape (Time-series)"]
        F3["Fact_CityMetrics & Benchmarks<br/>Isolated regional demographics"]
        DAX["_Measures Centralized DAX<br/>30+ KPIs across 7 Display Folders"]
    end

    W1 & K1 & M1 & B1 --> S2
    Stg1 & Stg2 & Stg3 & Stg4 & Stg5 --> Union
    Union --> Dedup --> Keys --> Dims
    Dims --> D_All
    Keys --> F1 & F2 & F3
    D_All & F1 & F2 & F3 --> DAX
```

---

## 2. Galaxy Schema (Fact Constellation) ERD

A single Star Schema cannot handle the distinct business grains present across Kickstarter campaigns, time-series scrapes, and demographic baselines. We implement a **Galaxy Schema** sharing conformed dimensions:

![Galaxy Schema ERD](../assets/diagrams/galaxy_schema_erd.png)

### Entity-Relationship Architecture:

```mermaid
erDiagram
    Dim_Project ||--o{ Fact_Campaign : "1 : * (ProjectKey)"
    Dim_Category ||--o{ Fact_Campaign : "1 : * (CategoryKey)"
    Dim_Location ||--o{ Fact_Campaign : "1 : * (LocationKey)"
    Dim_Currency ||--o{ Fact_Campaign : "1 : * (CurrencyKey)"
    Dim_Status ||--o{ Fact_Campaign : "1 : * (StatusKey)"
    Dim_Date ||--o{ Fact_Campaign : "1 : * (LaunchDateKey - Active)"
    Dim_Date ||..o{ Fact_Campaign : "1 : * (DeadlineDateKey - Inactive)"

    Dim_Project ||--o{ Fact_CampaignSnapshot : "1 : * (ProjectKey)"
    Dim_Category ||--o{ Fact_CampaignSnapshot : "1 : * (CategoryKey)"
    Dim_Currency ||--o{ Fact_CampaignSnapshot : "1 : * (CurrencyKey)"
    Dim_Status ||--o{ Fact_CampaignSnapshot : "1 : * (StatusKey)"
    Dim_Date ||--o{ Fact_CampaignSnapshot : "1 : * (SnapshotDateKey - Active)"

    Dim_Location ||--o{ Fact_CityMetrics : "1 : * (LocationKey)"

    Dim_Project {
        Int64 ProjectKey PK
        Int64 ProjectID NK
        Text ProjectName
        Text ProjectSlug
        Text Blurb
        Text Source_System
        Date Snapshot_Date
    }

    Dim_Category {
        Int64 CategoryKey PK
        Text Category
        Text Subcategory
    }

    Dim_Location {
        Int64 LocationKey PK
        Text CountryCode
        Text CountryName
        Text State
        Text County
        Text City
        Double Latitude
        Double Longitude
    }

    Dim_Date {
        Int64 DateKey PK
        Date Date
        Int64 Year
        Int64 MonthNumber
        Text MonthName
        Text YearMonth
        Text Quarter
    }

    Fact_Campaign {
        Int64 ProjectKey FK
        Int64 CategoryKey FK
        Int64 LocationKey FK
        Int64 CurrencyKey FK
        Int64 StatusKey FK
        Int64 LaunchDateKey FK
        Int64 DeadlineDateKey FK
        Currency GoalUSD
        Currency PledgedUSD
        Int64 BackerCount
        Int64 CampaignDurationDays
        Percentage GoalAchievementPct
    }

    Fact_CampaignSnapshot {
        Int64 ProjectKey FK
        Int64 CategoryKey FK
        Int64 CurrencyKey FK
        Int64 StatusKey FK
        Int64 SnapshotDateKey FK
        Currency GoalUSD
        Currency PledgedUSD
        Int64 BackerCount
    }

    Fact_CityMetrics {
        Int64 LocationKey FK
        Int64 CityPopulation
        Int64 CityAllTimeBackers
        Currency MeanPledgeCity
    }
```

---

## 3. Multi-Crawl Lifecycle & Deterministic Deduplication Machine

Because WebRobots crawls Kickstarter monthly, a campaign's state evolves over time. The deduplication engine guarantees canonical authority in `Fact_Campaign` while preserving trajectory in `Fact_CampaignSnapshot`:

```mermaid
stateDiagram-v2
    [*] --> Inception: Creator drafts campaign
    Inception --> Live: Launched (Observed in 2017 Scrape)
    
    state Live {
        [*] --> Crawl_2017_10: Backers: 120 | Pledged: $15,000
        Crawl_2017_10 --> Crawl_2017_11: Backers: 340 | Pledged: $42,000
    }

    Live --> Successful: Reached >= 100% Goal at Deadline
    Live --> Failed: Cutoff reached without funding
    Live --> Canceled: Creator canceled campaign

    state "Deduplication Engine Resolution" as Resolve {
        state "Observed in Multiple Snapshots" as Multi
        Multi --> SortRecency: Sort Snapshot_Date DESC
        SortRecency --> BufferMemory: Table.Buffer()
        BufferMemory --> KeepFirst: Table.Distinct({ProjectID})
    }

    Successful --> Resolve
    Failed --> Resolve
    Canceled --> Resolve

    Resolve --> Fact_Campaign: 1 Golden Record (Final State)
    Live --> Fact_CampaignSnapshot: Preserved as Time-Series Points
```

---

## 4. The Granularity Trap & Metric Isolation

Why can't `City_Pop` or `CountyMeanUSD` be placed directly inside `Fact_Campaign`?

```mermaid
flowchart TD
    subgraph WRONG["❌ Antipattern: Flatted Campaign Table"]
        F_Bad["Campaign Row 1: City = New York, Population = 8.3M, Pledged = $10k<br/>Campaign Row 2: City = New York, Population = 8.3M, Pledged = $25k<br/>Campaign Row 3: City = New York, Population = 8.3M, Pledged = $5k"]
        Calc_Bad["SUM(Population) = 24.9 Million! (3x Duplication Error)"]
        F_Bad --> Calc_Bad
    end

    subgraph RIGHT["✅ Analytics Engineering: Galaxy Constellation"]
        F_Good["Fact_Campaign: 1 row per project (Pledged USD, Backers)"]
        City_Good["Fact_CityMetrics: 1 row per city (City Population = 8.3M)"]
        Dim_L["Dim_Location: LocationKey for Joins"]
        Dim_L --> F_Good
        Dim_L --> City_Good
        Calc_Good["SUM(CityPopulation) = 8.3 Million (100% Mathematically Correct)"]
        City_Good --> Calc_Good
    end
```

---

## 5. Automated GitOps & Power BI CI/CD Architecture

How the automated version control watcher links Power BI Desktop directly to GitHub:

![GitOps PBIP Automation Flow](../assets/diagrams/git_pbip_automation_flow.png)

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Power BI Developer
    participant PBI as Power BI Desktop (.pbip)
    participant Watcher as src/auto_sync_powerbi.py Daemon
    participant Git as Local Git Index
    participant GH as GitHub Remote (origin main)
    participant CI as GitHub Actions CI Workflow

    Dev->>PBI: Edit DAX / Model / Layout & Press Ctrl + S
    PBI->>PBI: Write TMDL & JSON definition files
    Watcher->>Watcher: Detect file mtime change
    Note over Watcher: Debounce window (6 seconds) to ensure write completion
    Watcher->>Git: git add .
    Watcher->>Git: git diff --cached (Verify changes exist)
    Watcher->>Git: git commit -m "auto(powerbi): update definitions [timestamp]"
    Watcher->>GH: git push origin main
    GH->>CI: Trigger .github/workflows/ci.yml
    CI->>CI: Run Python syntax validation & PBIP integrity check
    CI-->>GH: ✅ All tests passed
```
