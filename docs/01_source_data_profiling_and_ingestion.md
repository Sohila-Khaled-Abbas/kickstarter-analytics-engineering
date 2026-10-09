# 01 — Source Data Profiling & Raw Ingestion Guide

## Comprehensive Source Profiling & Ingestion Blueprint

In an enterprise analytics engineering workflow, **never begin transformations before thoroughly profiling the raw data**. This document details the schema definitions, encodings, volume, known anomalies, and raw ingestion Power Query M scripts for each source asset located in `data/raw/`.

---

## 1. Raw Dataset Inventory & Profile

| Source Family | Physical Path | Primary File | Row Count (approx.) | Col Count | Default Encoding | Primary Business Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **MasterKickstarter** | `data/raw/master_kickstarter/` | `MasterKickstarter.csv` | ~99,000 | 57 | UTF-8 | Enriched historical portfolio with coordinates, city population, and pre-calculated regional features. |
| **County Benchmark** | `data/raw/master_kickstarter/` | `County.csv` | ~3,100 | 9 | UTF-8 | Benchmark metrics aggregated by US county (`subregion`) and state (`region`). |
| **State Benchmark** | `data/raw/master_kickstarter/` | `Mapping.csv` | ~51 | 8 | UTF-8 | Benchmark metrics aggregated by US state (mean pledges, building duration, goals). |
| **Kaggle 2016** | `data/raw/kickstarter_projects/` | `ks-projects-201612.csv` | ~323,000 | 17 | **Windows-1252** | Historical Kaggle snapshot (up to Dec 2016). Contains unquoted commas and trailing whitespace. |
| **Kaggle 2018** | `data/raw/kickstarter_projects/` | `ks-projects-201801.csv` | ~378,000 | 15 | UTF-8 | Complete Kaggle historical archive with fixusd normalized conversion columns. |
| **WebRobots Master** | `data/raw/` | `WebRobots_Enrichment_Master.csv` | ~210,000 | 12 | UTF-8 | Longitudinal consolidated master extracted from WebRobots monthly/yearly crawls. |
| **WebRobots Crawls** | `data/raw/webrobots/` | `*.csv`, `*.json` (361 files) | 5M+ raw events | Dynamic | UTF-8 | Recurring web scrape dumps from 2014 to 2026 tracking ongoing campaign funding trajectories. |

---

## 2. Schema Deep-Dive & Anomalies by Source

### A. MasterKickstarter (`MasterKickstarter.csv`)
This dataset contains 57 columns combining campaign characteristics with city-level geospatial attributes.

```text
Key Identifiers:
  - id                         : Unique Kickstarter Campaign ID (Integer)
  - name, slug, blurb          : Descriptive text content

Financials:
  - goal, pledged              : Nominal values in local currency
  - pledgedUSD                 : Pledged amount normalized to USD
  - Ex_USd                     : Historical exchange rate applied
  - currency, currency_symbol  : Currency metadata

Temporal Attributes:
  - deadline, state_changed_at, created_at, launched_at : String timestamps
  - deadlineTime, created_atTime, launched_atTime       : Epoch integer timestamps (Unix seconds)
  - deadlineYM, created_atYM, launched_atYM             : Aggregated Year-Month strings (e.g., '2015-04')
  - deadlineY, created_atY, launched_atY                : Aggregated Year integers

Geographic Attributes:
  - Country, State, County, City : Hierarchical location strings
  - Latitude, Longitude          : Geographic coordinates (Floating decimal)
  - City_Pop                     : Demographic population of the campaign's city

Regional Pre-Calculations (Separate Grain):
  - Backers_as_Prct_of_Pop, CityBackersYear, Mean_Pledge_City, etc.
```

> [!WARNING]
> **Granularity Trap in MasterKickstarter**:
> `City_Pop` and `Mean_Pledge_City` belong to the **City** grain, not the **Campaign** grain. If left denormalized inside the campaign table, calculating `SUM(City_Pop)` across campaigns will cause massive, incorrect multiplication. These fields must be split into `Fact_CityMetrics` during dimensional modeling.

---

### B. Kaggle 2016 Snapshot (`ks-projects-201612.csv`)
Contains historical records, but exhibits severe real-world data issues:

1. **Trailing Spaces in Column Headers**: Notice the trailing spaces: `'ID '`, `'name '`, `'category '`, `'main_category '`, `'currency '`, `'deadline '`, `'goal '`, `'launched '`, `'pledged '`, `'state '`, `'backers '`, `'country '`, `'usd pledged '`.
2. **Encoding**: Contains special characters encoded in `Windows-1252` (`CodePage = 1252`). Reading as standard UTF-8 causes character decoding crashes (`0x99`).
3. **Column Drift Anomalies**: Unescaped commas in project blurbs caused text to spill into phantom columns: `Unnamed: 13`, `Unnamed: 14`, `Unnamed: 15`, `Unnamed: 16`. These four phantom columns must be filtered out in Power Query.
4. **Missing Goal USD**: Kaggle 2016 only provides `usd pledged `, but **not** `goal_usd`. For non-USD currencies, Goal USD must be calculated or left null with explicit metadata flags.

---

### C. Kaggle 2018 Snapshot (`ks-projects-201801.csv`)
The cleanest historical snapshot.
- Contains 15 clean columns.
- Provides `usd_pledged_real` and `usd_goal_real` using Fixer.io historical exchange rates.
- Uses standard UTF-8 encoding.
- Date fields: `deadline` (Date string: `YYYY-MM-DD`), `launched` (Datetime string: `YYYY-MM-DD HH:MM:SS`).

---

### D. WebRobots Crawls & Master
WebRobots crawls Kickstarter monthly by querying category endpoints.
- **Internal Duplication**: Because Kickstarter allows projects to belong to subcategories and featured lists, a single monthly crawl often scrapes the same project multiple times within hours.
- **Dynamic Statuses**: A campaign observed in October 2017 as `live` will be re-scraped in November 2017 as `successful`. In longitudinal tracking, both are valuable; in portfolio reporting, only the latest state is valid.

---

## 3. Power Query Raw Ingestion Scripts (Group: `01_Sources`)

These queries establish the raw connection to the CSV files using the `DataFolderPath` parameter.
**Mandatory Analytics Engineering Rule**: All `Src_*` queries must have **Enable Load = False**.

### 1. `Src_Kaggle_2016`
```powerquery
let
    Source = Csv.Document(
        File.Contents(DataFolderPath & "raw\kickstarter_projects\ks-projects-201612.csv"),
        [
            Delimiter = ",",
            Columns = 17,
            Encoding = 1252,
            QuoteStyle = QuoteStyle.Csv
        ]
    ),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars = true])
in
    #"Promoted Headers"
```

### 2. `Src_Kaggle_2018`
```powerquery
let
    Source = Csv.Document(
        File.Contents(DataFolderPath & "raw\kickstarter_projects\ks-projects-201801.csv"),
        [
            Delimiter = ",",
            Columns = 15,
            Encoding = 65001,
            QuoteStyle = QuoteStyle.None
        ]
    ),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars = true])
in
    #"Promoted Headers"
```

### 3. `Src_MasterKickstarter`
```powerquery
let
    Source = Csv.Document(
        File.Contents(DataFolderPath & "raw\master_kickstarter\MasterKickstarter.csv"),
        [
            Delimiter = ",",
            Columns = 57,
            Encoding = 65001,
            QuoteStyle = QuoteStyle.Csv
        ]
    ),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars = true])
in
    #"Promoted Headers"
```

### 4. `Src_WebRobots_Latest`
```powerquery
let
    Source = Csv.Document(
        File.Contents(DataFolderPath & "raw\WebRobots_Enrichment_Master.csv"),
        [
            Delimiter = ",",
            Columns = 12,
            Encoding = 65001,
            QuoteStyle = QuoteStyle.None
        ]
    ),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars = true])
in
    #"Promoted Headers"
```

### 5. `Src_County`
```powerquery
let
    Source = Csv.Document(
        File.Contents(DataFolderPath & "raw\master_kickstarter\County.csv"),
        [
            Delimiter = ",",
            Columns = 9,
            Encoding = 65001,
            QuoteStyle = QuoteStyle.None
        ]
    ),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    #"Removed System Index" = Table.RemoveColumns(#"Promoted Headers", {""})
in
    #"Removed System Index"
```

### 6. `Src_Mapping`
```powerquery
let
    Source = Csv.Document(
        File.Contents(DataFolderPath & "raw\master_kickstarter\Mapping.csv"),
        [
            Delimiter = ",",
            Columns = 8,
            Encoding = 65001,
            QuoteStyle = QuoteStyle.None
        ]
    ),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars = true])
in
    #"Promoted Headers"
```

---

## 4. Verification & Testing Steps

After pasting each source query into the Power Query Advanced Editor:
1. Confirm that **Source** connects without error.
2. Confirm the number of columns matches the documented column count.
3. Verify that `Enable Load` is unchecked (query name displayed in italics).
4. Save and inspect the preview table to confirm zero `#ERROR` cells in the first 1,000 rows.
