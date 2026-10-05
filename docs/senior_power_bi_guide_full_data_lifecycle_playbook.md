# Kickstarter Analytics Engineering & Power BI Playbook

## Full Data Lifecycle: Web Robots + Kaggle + Python + Power Query + Power BI

> **Project objective:** Build a production-style analytics engineering pipeline and Power BI semantic model for studying Kickstarter campaign performance, failure patterns, funding behavior, geography, category effects, and data-quality issues — while minimizing data duplication, unnecessary downloads, Power Query workload, and VertiPaq memory usage.

---

## 1. Project Data Sources

This project combines three externally sourced Kickstarter datasets plus project-local mapping files.

### 1.1 Web Robots — historical Kickstarter crawl archive

Source:

<https://webrobots.io/kickstarter-datasets/>

Web Robots states that it crawls Kickstarter projects and publishes CSV and JSON datasets. It says monthly crawling began in March 2016, while older historical snapshots are also available. It also warns that after December 2015 the collection process traversed sub-categories, which can create duplicate project rows because a project can appear in multiple categories. The JSON files from December 2015 onward use JSON Streaming / newline-delimited JSON, and the compressed files are around 100 MB while the uncompressed data is around 600 MB.

**This source is the primary source for the temporal/snapshot component of the project.**

### 1.2 Kaggle — MasterKickstarter

Source:

<https://www.kaggle.com/wood2174/mapkickstarter>

File used in this project:

```text
MasterKickstarter.csv
```

A publicly indexed analysis using this exact dataset describes it as a 56 MB file with about 99,000 project records covering 2009–2017 and 57 attributes. Use this dataset as a **historical/enrichment source**, not as another fact table to blindly append to the Web Robots snapshots.

Reference used for the published dataset description:
<https://github.com/LeGriffon/Kickstarters_Data_Analysis>

### 1.3 Kaggle — Kickstarter Projects by kemical

Source:

<https://www.kaggle.com/datasets/kemical/kickstarter-projects>

The commonly used 2018 file contains 378,661 projects and 15 columns:

```text
ID
name
category
main_category
currency
deadline
goal
launched
pledged
state
backers
country
usd pledged
usd_pledged_real
usd_goal_real
```

The older 2016 file uses the earlier schema and notably does not contain the two `_real` USD fields that exist in the 2018 file. Older copies can also contain `Unnamed:*` columns caused by malformed/extra CSV fields.

Reference examples confirming the schemas:
<https://criskrus.github.io/kaggle/06-data-cleaning/04-character-encodings/character-encodings.html>
<https://rstudio-pubs-static.s3.amazonaws.com/377754_67f4e5068f1c43498d6a0e45bf5c2cf7.html>

### 1.4 Project-local geography files

The project also contains:

```text
Mapping.csv
County.csv
```

The existing project guide describes these as geography-level pre-aggregated tables rather than raw campaign rows. Preserve them as separate analytical tables and validate their actual grain/columns before defining relationships.

---

# 2. Critical Architecture Decision: Do NOT Build One Giant Append

The previous guide recommended appending all Kaggle tables and Web Robots snapshots into one `Fact_Campaigns_Raw` table and then using `Table.Buffer` to force a deduplication order.

**Do not use that design for this project.**

There are three different concepts that must remain separate:

1. **The same project observed at different times** — this is historical information, not a duplicate.
2. **The same project repeated within the same Web Robots scrape** — this is a real duplicate caused by the crawler's multi-category collection process.
3. **The same project appearing in multiple independent source datasets** — this is a cross-source overlap that must be audited and reconciled, not blindly appended.

Microsoft's Power BI guidance also recommends keeping fact tables at a consistent grain and using star-schema modeling. citeturn314009search1

### Target architecture

```text
                         ┌──────────────────────────┐
                         │ Web Robots archive       │
                         │ CSV / JSON.GZ snapshots  │
                         └────────────┬─────────────┘
                                      │
                         latest-per-year selection
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │ Python Raw / Silver      │
                         │ normalize + dedupe      │
                         │ snapshot metadata       │
                         └────────────┬─────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
      Kaggle Kemical          Kaggle Master          Mapping / County
      2016 / 2018             historical/enrich.     geography aggregates
              │                       │                       │
              └───────────────────────┼───────────────────────┘
                                      ▼
                         ┌──────────────────────────┐
                         │ Source Audit /           │
                         │ Reconciliation Layer     │
                         │ project_id overlap       │
                         └────────────┬─────────────┘
                                      │
                  ┌───────────────────┴──────────────────┐
                  ▼                                      ▼
      Fact_Project_Snapshot                    Dim_Project / Fact_Project
      project_id + snapshot_date              one canonical project row
                  │                                      │
                  └──────────────────┬───────────────────┘
                                     ▼
                           Power BI Star Schema
                                     │
                                     ▼
                           DAX Measures / Reports
```

---

# 3. Download Strategy — Minimize Internet Usage First

## 3.1 Required Web Robots strategy

The downloader must follow exactly this rule:

> **Latest-per-year + CSV-preferred / JSON-fallback**

For each year:

1. Find all available Web Robots scrape dates.
2. Select the latest scrape date in that year.
3. If that exact scrape has both CSV and JSON, download **CSV only**.
4. If the latest scrape has no CSV, download **JSON only**.
5. Never download both formats for the same scrape.
6. Never download older monthly snapshots unless the project explicitly needs monthly change analysis.

This is the most important download optimization because the Web Robots archive has monthly snapshots, but many monthly snapshots overlap heavily.

## 3.2 Current latest-per-year selection

Based on the current Web Robots page, the recommended selection is:

| Year | Latest scrape | Selected format |
|---|---|---|
| 2026 | 2026-09-10 | CSV |
| 2025 | 2025-12-18 | CSV |
| 2024 | 2024-12-12 | CSV |
| 2023 | 2023-12-14 | CSV |
| 2022 | 2022-12-15 | CSV |
| 2021 | 2021-12-14 | CSV |
| 2020 | 2020-12-17 | CSV |
| 2019 | 2019-12-12 | CSV |
| 2018 | 2018-12-13 | JSON |
| 2017 | 2017-12-15 | JSON |
| 2016 | 2016-12-15 | JSON |
| 2015 | 2015-12-17 | JSON |
| 2014 | 2014-12-02 | JSON |

The Web Robots page currently lists CSV for the 2020–2026 annual endpoints, CSV for 2019 from May onward, JSON-only snapshots throughout 2018–2016, and JSON for the latest 2015 and 2014 snapshots; 2015-10-22 is a special older snapshot that also has CSV, but it is not the latest 2015 scrape. citeturn688018view0

### Expected local structure

```text
D:\courses\Data Analysis 26-27\Projects\Kickstarter Projects\data\
│
├── 2026\
│   └── Kickstarter_2026-09-10....zip
├── 2025\
│   └── Kickstarter_2025-12-18....zip
├── 2024\
│   └── Kickstarter_2024-12-12....zip
├── 2023\
├── 2022\
├── 2021\
├── 2020\
├── 2019\
├── 2018\
│   └── Kickstarter_2018-12-13....json.gz
├── 2017\
│   └── Kickstarter_2017-12-15....json.gz
├── 2016\
│   └── Kickstarter_2016-12-15....json.gz
├── 2015\
│   └── Kickstarter_2015-12-17....json.gz
└── 2014\
    └── Kickstarter_2014-12-02....json.gz
```

## 3.3 Turbo downloader requirements

Use an asynchronous HTTP library such as `httpx` or `aiohttp` rather than sequential `requests` calls.

Recommended capabilities:

- connection pooling
- HTTP/2 where supported
- concurrent downloads
- byte-range requests for large files where the server supports `Range`
- resumable `.part` segments
- retries with exponential backoff
- final file-size validation
- selection manifest before downloading
- download manifest after downloading
- no re-download of complete files

Recommended initial tuning:

```python
MAX_CONNECTIONS = 64
SEGMENTS_PER_FILE = 16
CHUNK_SIZE = 8 * 1024 * 1024
MAX_RETRIES = 6
```

Increase concurrency gradually. The goal is maximum useful throughput, not maximum request count. Excessive concurrency can trigger throttling and can become slower.

### Non-negotiable downloader safeguards

The downloader must never:

- download CSV + JSON for the same selected scrape
- download every monthly Web Robots file by default
- restart a completed file
- treat `.part` files as complete datasets
- delete an existing dataset without an explicit cleanup flag
- silently replace a newer selected file with an older scrape

---

# 4. Python Raw → Silver Layer

Power BI should **not** ingest the raw Web Robots archive directly.

CSV and JSON files do not provide database-style query processing, so Power Query has to perform much of the transformation work locally. Microsoft recommends minimizing work done by the Power Query engine for large models and, where possible, preparing data upstream. citeturn314009search0turn314009search2

## 4.1 Recommended Python stack

```text
httpx / aiohttp      HTTP download
orjson               fast JSON parsing
Polars               vectorized transformation
DuckDB               analytical SQL + Parquet processing
PyArrow              Parquet interoperability
pandas               optional compatibility layer
```

Use **Polars + DuckDB + Parquet** for the heavy preparation stage. Keep pandas for compatibility or small diagnostic operations, not as the default engine for the entire historical archive.

## 4.2 Bronze / Raw

Keep downloaded source files unchanged:

```text
raw/
  webrobots/
    2026/
    2025/
    ...
  kaggle/
    MasterKickstarter.csv
    ks-projects-201612.csv
    ks-projects-201801.csv
    Mapping.csv
    County.csv
```

Never edit the raw files in place.

## 4.3 Silver

Convert each selected Web Robots file into a normalized analytical format:

```text
silver/
  webrobots_snapshot.parquet
  kaggle_kemical_201801.parquet
  kaggle_kemical_201612.parquet
  kaggle_masterkickstarter.parquet
  mapping.parquet
  county.parquet
```

Add lineage columns:

```text
_source_system
_source_dataset
_source_file
_snapshot_date
_ingestion_timestamp
```

These columns are critical for auditability.

---

# 5. Web Robots Deduplication Rules

Web Robots explicitly warns that the post-December-2015 collection method traverses sub-categories and can produce duplication when a project is listed in multiple categories. citeturn688018view0

## 5.1 Correct duplicate key

Inside one Web Robots snapshot:

```text
project_id
```

should be the campaign business key.

Therefore:

```text
(project_id, snapshot_date)
```

is the natural key for a historical snapshot table.

## 5.2 Do NOT use project name as the key

Do not deduplicate by:

```text
name
```

Names are not guaranteed to be unique and can change in source systems.

## 5.3 Do NOT treat annual observations as duplicates

Example:

```text
Project 12345
    2018 snapshot → failed
    2019 snapshot → successful
    2020 snapshot → successful
```

These are **three observations of one project**, not three duplicate rows.

For temporal analysis, retain them in:

```text
Fact_Project_Snapshot
```

For a one-row-per-project analytical dimension, derive:

```text
Dim_Project
```

or:

```text
Fact_Project_Current
```

using a documented survivorship rule.

---

# 6. Kaggle Dataset Reconciliation

## 6.1 Kemical 2016 vs 2018

Do NOT append the two Kaggle files directly into one fact table without a source/release field.

The 2016 dataset has the earlier schema, including:

```text
ID
name
category
main_category
currency
deadline
goal
launched
pledged
state
backers
country
usd pledged
```

The 2018 dataset adds:

```text
usd_pledged_real
usd_goal_real
```

and is documented as 378,661 rows × 15 columns. citeturn375239search0turn375239search2

### Harmonize to canonical names

```text
ID                  → project_id
name                → project_name
category            → subcategory_name
main_category       → category_name
currency            → currency_code
deadline            → deadline_at
goal                → goal_amount
launched            → launched_at
pledged             → pledged_amount
state               → project_state
backers             → backer_count
country             → country_code
usd pledged         → pledged_usd_source
usd_pledged_real    → pledged_usd_real
usd_goal_real       → goal_usd_real
```

Keep the original source column where it is analytically useful. Do not destroy the raw meaning just to force a matching name.

## 6.2 Windows encoding issue in the older Kaggle file

The widely used 2016 file may require `Windows-1252` decoding. This is a documented issue in examples using the Kaggle dataset. citeturn375239search0

Python example:

```python
import polars as pl

df_2016 = pl.read_csv(
    "ks-projects-201612.csv",
    encoding="windows-1252",
    ignore_errors=True,
)
```

Before committing the transformation, profile the actual file present in the project because downloads and repackaged copies can differ.

---

# 7. MasterKickstarter: Enrichment, Not Blind Append

`MasterKickstarter.csv` overlaps substantially with the Kemical and Web Robots project universe. Therefore:

**Do not do this:**

```text
MasterKickstarter
    + Kemical 2016
    + Kemical 2018
    + Web Robots
    = giant Fact_Campaigns
```

That architecture causes duplicate project IDs and makes measures such as:

```text
COUNTROWS(Fact_Campaigns)
SUM(pledged_usd)
```

misleading.

Instead, keep separate source-stage tables and create an overlap audit.

### Required overlap audit

For every pair of sources calculate:

```text
Source A rows
Source A distinct project IDs
Source B rows
Source B distinct project IDs
Matching project IDs
A-only IDs
B-only IDs
```

The central key is:

```text
project_id
```

### Matching rule

Primary:

```text
ID = project_id
```

Secondary diagnostic only:

```text
normalized project name + launch date + country
```

Never use the secondary match to silently overwrite the primary ID-based relationship.

---

# 8. The Two-Fact-Table Strategy

For this project, a single fact table is not enough.

## 8.1 Fact_Project_Snapshot

**Grain:** one row per Kickstarter project per selected Web Robots snapshot.

Columns:

```text
project_id
snapshot_date
project_name
category_id
location_id
currency_key
launched_date_key
deadline_date_key
goal_usd
pledged_usd
backer_count
project_state
source_system
```

Purpose:

- outcome changes over time
- yearly project counts
- state transitions
- funding trend analysis
- category growth
- geographic movement
- source coverage

## 8.2 Fact_Project

**Grain:** one row per unique Kickstarter project.

Purpose:

- canonical portfolio analysis
- unique project count
- overall success rate
- funding performance
- project-level segmentation

This table must be generated from an explicit survivorship rule.

Recommended rule:

```text
1. Prefer the latest Web Robots observation for project-level current values.
2. If project is absent from Web Robots, retain the best available Kaggle observation.
3. Keep source indicators showing where the record came from.
4. Never hide source conflicts.
```

## 8.3 Why both tables matter

A project appearing in 2018, 2019 and 2020 should count as:

```text
1 unique project
```

in `Fact_Project`, but:

```text
3 project observations
```

in `Fact_Project_Snapshot`.

This distinction prevents the most common double-counting error in this project.

---

# 9. Power Query Architecture

Microsoft recommends filtering early, using correct data types, parameterizing sources, splitting large queries into modules, and documenting the transformation pipeline. citeturn314009search2

Power Query also does not provide query folding for ordinary CSV/Excel file sources, so heavy work should be moved upstream into the Python/DuckDB/Parquet layer where possible. citeturn314009search5

## 9.1 Query groups

Create these Power Query groups:

```text
00 Parameters
01 Sources
02 Staging
03 Conformed
04 Dimensions
05 Facts
99 QA
```

## 9.2 Parameters

Create:

```text
DataFolderPath
```

Value:

```text
D:\courses\Data Analysis 26-27\Projects\Kickstarter Projects\data\
```

Also create:

```text
SilverFolderPath
```

Example:

```text
D:\courses\Data Analysis 26-27\Projects\Kickstarter Projects\analytics_engineering\silver\
```

Use parameters instead of hard-coded paths.

---

# 10. Recommended Power Query Flow

```text
Source Parquet / CSV
        ↓
Select required columns
        ↓
Set data types
        ↓
Add source lineage
        ↓
Standardize field names
        ↓
Validate project_id
        ↓
Remove exact duplicates within snapshot
        ↓
Create dimensions
        ↓
Create fact tables
        ↓
QA
        ↓
Load to model
```

## 10.1 GUI + M together

Use the Power Query GUI for:

- selecting columns
- renaming columns
- changing obvious data types
- filtering null project IDs
- reviewing column quality
- creating query groups
- creating references
- documenting steps

Use M code for:

- reusable source functions
- dynamic file selection
- canonical column mapping
- complex deduplication
- deterministic conflict handling
- parameterized logic
- QA assertions

Do not use M merely to make a transformation look advanced. Every M step should reduce ambiguity, improve reuse, or improve maintainability.

---

# 11. Do NOT Use Table.Buffer as a General Deduplication Trick

The old guide recommended:

```powerquery
SortedRows = Table.Sort(...)
BufferedTable = Table.Buffer(SortedRows)
Table.Distinct(BufferedTable, {"project_id"})
```

This should not be the default architecture.

Microsoft specifically documents that `Table.Buffer` materializes a table for the current query execution and does not prevent referenced queries from retrieving and buffering the underlying data again. It can therefore increase memory consumption and does not solve repeated execution across referenced queries. citeturn314009search8

Prefer:

1. deduplicate upstream in Python/DuckDB
2. use deterministic SQL/window logic for large datasets
3. reserve `Table.Buffer` for narrowly justified cases after measurement

### Better deterministic rule

For one snapshot:

```sql
ROW_NUMBER() OVER (
    PARTITION BY project_id
    ORDER BY source_record_quality DESC
)
```

Keep `rn = 1`.

The exact tie-breaker must be documented.

---

# 12. Canonical Data Types

Use the following target types before loading the model:

| Column | Target type |
|---|---|
| project_id | Text or Int64, consistently across sources |
| project_name | Text |
| category_name | Text |
| subcategory_name | Text |
| country_code | Text |
| currency_code | Text |
| launched_at | DateTime |
| deadline_at | DateTime |
| goal_usd | Decimal Number |
| pledged_usd | Decimal Number |
| backer_count | Whole Number |
| project_state | Text |
| snapshot_date | Date |

Do not keep duplicated numeric representations unless they have different meanings.

For example:

```text
goal
usd_goal_real
```

should not both be used as `Goal USD`.

Use:

```text
goal_amount_original
currency_code
goal_usd
```

so the meaning is explicit.

---

# 13. Currency Governance

The 2018 Kaggle dataset contains:

```text
goal
pledged
currency
usd pledged
usd_pledged_real
usd_goal_real
```

The dataset documentation/examples identify `usd_pledged_real` and `usd_goal_real` as USD-converted fields using a different conversion source from the older `usd pledged` field. citeturn375239search2

For comparable cross-currency analytics:

**Prefer:**

```text
goal_usd = usd_goal_real
actionable_pledged_usd = usd_pledged_real
```

when present.

For the 2016 file, which lacks these newer real-conversion fields, preserve the source's available USD value and label it clearly, for example:

```text
pledged_usd_source
```

Do not silently pretend that every USD field was generated with the same methodology.

---

# 14. Star Schema for Power BI

Microsoft recommends a star schema in which dimensions support filtering/grouping and fact tables support aggregation, with a consistent fact-table grain. citeturn314009search1

### Target model

```text
                         Dim_Date
                            │
                            │ 1:M
                            ▼
Dim_Category ────────► Fact_Project_Snapshot ◄────── Dim_Location
                            │
                            │
                            ▼
                       Dim_Project
```

A more practical Power BI implementation is:

```text
Dim_Date
   │
   ├───────────────► Fact_Project
   │
   └───────────────► Fact_Project_Snapshot

Dim_Category
   │
   ├───────────────► Fact_Project
   └───────────────► Fact_Project_Snapshot

Dim_Location
   │
   ├───────────────► Fact_Project
   └───────────────► Fact_Project_Snapshot

Dim_Currency
   │
   ├───────────────► Fact_Project
   └───────────────► Fact_Project_Snapshot
```

Keep geography aggregate tables separate unless their grain is proven compatible with the dimension being related.

---

# 15. Dimension Design

## Dim_Date

Columns:

```text
DateKey
Date
Year
Quarter
Month Number
Month Name
Year-Month
```

Use `launched_at` as the primary analytical date for campaign-start trends.

Use role-playing date dimensions or inactive relationships if deadline analysis is also required.

## Dim_Category

```text
CategoryKey
MainCategory
Subcategory
```

Do not use category names directly as foreign keys in the fact.

## Dim_Location

Keep only the geographic levels actually supported by the datasets:

```text
LocationKey
Country
State
County/Subregion
City
```

Do not manufacture a state/county value where the source does not support it.

## Dim_Currency

```text
CurrencyKey
CurrencyCode
CurrencyName
```

## Dim_Project

Use one row per unique `project_id`.

Suggested attributes:

```text
ProjectKey
project_id
ProjectName
CategoryKey
LocationKey
CurrencyKey
FirstLaunchDate
LatestKnownSnapshotDate
CurrentState
```

---

# 16. Geography: Mapping.csv and County.csv

Treat these files according to their actual grain.

The existing project documentation describes `Mapping.csv` as state-level metrics and `County.csv` as county/subregion metrics. fileciteturn1file0L40-L43

Do not merge these aggregated metrics into the campaign-level fact table.

Correct pattern:

```text
Dim_Location
   │
   ├── State
   └── County/Subregion
        │
        ├────────► Dim_State_Metrics
        └────────► Dim_County_Metrics
```

However, before creating these relationships, verify:

- uniqueness of the key on the dimension side
- case normalization
- whitespace normalization
- spelling differences
- state abbreviations vs full names
- whether `subregion` means U.S. county in every row

Never create a many-to-many relationship just because the two tables share a column name.

---

# 17. QA — The Most Important Analytics Engineering Layer

Create a dedicated `99 QA` query group.

## 17.1 Row-count tests

Track:

```text
Raw rows
Distinct project IDs
Rows after source-level deduplication
Rows in Fact_Project_Snapshot
Distinct project IDs in Fact_Project
```

## 17.2 Duplicate tests

For `Fact_Project`:

```text
COUNTROWS = DISTINCTCOUNT(project_id)
```

For `Fact_Project_Snapshot`:

```text
COUNTROWS = DISTINCTCOUNT(project_id & snapshot_date)
```

## 17.3 Null key tests

```text
project_id IS NOT NULL
snapshot_date IS NOT NULL
```

## 17.4 Numeric validation

Flag:

```text
goal < 0
pledged < 0
backers < 0
funding_ratio < 0
```

Do not automatically delete suspicious records. Create a QA flag and investigate.

## 17.5 State validation

Standardize case and spelling:

```text
successful
failed
canceled
live
suspended
```

Use a governed normalized status field instead of allowing multiple spelling/case variants to drive measures.

---

# 18. Source Overlap Audit

Build a table like:

| Source A | Source B | Matching IDs | A only | B only |
|---|---|---:|---:|---:|
| Kemical 2018 | Web Robots | calculated | calculated | calculated |
| MasterKickstarter | Kemical 2018 | calculated | calculated | calculated |
| MasterKickstarter | Web Robots | calculated | calculated | calculated |

Then create a second audit:

```text
Project ID
Field
Source A Value
Source B Value
Conflict Flag
Preferred Value
Preference Rule
```

Example:

```text
123456
pledged_usd
50000
52375
TRUE
52375
latest Web Robots observation
```

Do not silently overwrite the discrepancy.

---

# 19. Analytical Metrics

## Portfolio metrics

```DAX
Projects = DISTINCTCOUNT ( Fact_Project[project_id] )

Successful Projects =
CALCULATE (
    [Projects],
    Fact_Project[project_state] = "successful"
)

Success Rate =
DIVIDE (
    [Successful Projects],
    [Projects]
)

Total Goal USD =
SUM ( Fact_Project[goal_usd] )

Total Pledged USD =
SUM ( Fact_Project[pledged_usd] )

Total Backers =
SUM ( Fact_Project[backer_count] )
```

## Funding efficiency

```DAX
Funding Ratio =
DIVIDE (
    [Total Pledged USD],
    [Total Goal USD]
)
```

Do not average row-level funding ratios when a weighted portfolio ratio is the intended measure.

## Snapshot analysis

```DAX
Snapshot Projects =
DISTINCTCOUNT ( Fact_Project_Snapshot[project_id] )
```

Use `Dim_Date` / snapshot date for temporal analysis.

---

# 20. Issues / Problem Analysis Framework

The dashboard should not stop at descriptive KPIs.

The analytical narrative should answer:

```text
What happened?
       ↓
Where did it happen?
       ↓
Which categories / markets are affected?
       ↓
What factors are associated with the outcome?
       ↓
How large is the opportunity / risk?
       ↓
What should the business or creator do next?
```

## Core issues to investigate

### Issue 1 — High failure concentration

Questions:

- Which categories have the lowest success rates?
- Are failures concentrated in certain countries?
- Is failure related to goal size?
- Does campaign duration correlate with outcome?

### Issue 2 — Goal-setting problem

Compare:

```text
Goal USD
Pledged USD
Funding Ratio
State
```

Segment by:

```text
Category
Country
Launch Year
Goal Bands
```

### Issue 3 — Geographic imbalance

Use:

```text
Dim_Location
Dim_State_Metrics
Dim_County_Metrics
```

but keep aggregate geography metrics separate from campaign-level facts.

### Issue 4 — Category performance

Compare:

```text
Projects
Success Rate
Median Goal
Median Pledged
Median Funding Ratio
Backers
```

Prefer median alongside average because Kickstarter distributions can be heavily skewed.

### Issue 5 — Temporal changes

Use `Fact_Project_Snapshot` to examine:

```text
project state changes
funding growth
category mix
geography mix
new project volume
```

Do not interpret a repeated project observation as a new project.

---

# 21. Advanced DAX Measures for Diagnostic Analysis

```DAX
Median Goal USD =
MEDIAN ( Fact_Project[goal_usd] )

Median Pledged USD =
MEDIAN ( Fact_Project[pledged_usd] )

Median Backers =
MEDIAN ( Fact_Project[backer_count] )

Successful Funding Ratio =
CALCULATE (
    [Funding Ratio],
    Fact_Project[project_state] = "successful"
)

Failed Projects =
CALCULATE (
    [Projects],
    Fact_Project[project_state] = "failed"
)
```

Create measures rather than exposing raw columns for every business calculation. This supports semantic consistency and reduces metric duplication.

---

# 22. Power BI Performance Rules

## Reduce rows before Power BI

Do as much large-scale preparation as possible in:

```text
Python
Polars
DuckDB
Parquet
```

Then load curated Parquet files into Power BI.

Power Query supports the Parquet connector in Power BI Desktop. citeturn314009search6

## Reduce columns

Load only columns required for:

- filtering
- grouping
- relationships
- measures
- drill-through/detail analysis

## Use dimensions for text

Avoid repeating high-cardinality text fields in large fact tables.

## Prefer explicit measures

Create governed DAX measures for:

```text
Project Count
Success Rate
Goal
Pledged
Backers
Funding Ratio
```

## Keep technical lineage fields hidden

Hide:

```text
_source_file
_source_system
_ingestion_timestamp
```

from normal report users while retaining them for QA and audit pages.

---

# 23. Power Query: Practical M Pattern

A reusable normalization function should be preferred over copy-pasting dozens of transformations.

Example:

```powerquery
(tbl as table, sourceName as text, snapshotDate as nullable date) as table =>
let
    Renamed = Table.RenameColumns(
        tbl,
        {
            {"ID", "project_id"},
            {"name", "project_name"},
            {"main_category", "category_name"},
            {"category", "subcategory_name"},
            {"currency", "currency_code"},
            {"deadline", "deadline_at"},
            {"launched", "launched_at"},
            {"state", "project_state"},
            {"backers", "backer_count"}
        },
        MissingField.Ignore
    ),

    WithSource = Table.AddColumn(
        Renamed,
        "_source_system",
        each sourceName,
        type text
    ),

    WithSnapshot = Table.AddColumn(
        WithSource,
        "snapshot_date",
        each snapshotDate,
        type date
    )

in
    WithSnapshot
```

The exact source columns should be checked before applying this function because the 2016 and 2018 Kaggle files are not identical.

---

# 24. Power Query: Deterministic Duplicate Check

Use a QA query rather than blindly deleting rows:

```powerquery
let
    Source = Fact_Project_Snapshot,

    Grouped = Table.Group(
        Source,
        {"project_id", "snapshot_date"},
        {
            {"RowCount", each Table.RowCount(_), Int64.Type}
        }
    ),

    DuplicatesOnly = Table.SelectRows(
        Grouped,
        each [RowCount] > 1
    )

in
    DuplicatesOnly
```

This tells you **where duplicates exist** before you remove them.

---

# 25. Recommended Repository Structure

```text
Kickstarter Projects/
│
├── data/                         # immutable downloaded raw data
│   ├── 2026/
│   ├── 2025/
│   ├── ...
│   └── 2014/
│
├── analytics_engineering/
│   ├── bronze/
│   ├── silver/
│   │   ├── webrobots/
│   │   ├── kaggle/
│   │   └── geography/
│   ├── gold/
│   │   ├── fact_project.parquet
│   │   ├── fact_project_snapshot.parquet
│   │   ├── dim_date.parquet
│   │   ├── dim_project.parquet
│   │   ├── dim_category.parquet
│   │   ├── dim_location.parquet
│   │   └── dim_currency.parquet
│   └── audit/
│       ├── source_profile.csv
│       ├── source_overlap.csv
│       ├── field_conflicts.csv
│       └── duplicate_projects.csv
│
├── power_bi/
│   ├── Kickstarter.pbix
│   └── documentation/
│
└── scripts/
    ├── download_kickstarter_latest_per_year.py
    ├── prepare_webrobots.py
    ├── reconcile_kaggle_sources.py
    └── build_kickstarter_warehouse.py
```

---

# 26. End-to-End Run Order

Run the project in this order.

### Step 1 — Download

```text
Web Robots
    ↓
latest-per-year
    ↓
CSV preferred
    ↓
JSON fallback
```

### Step 2 — Validate downloaded files

Check:

```text
filename
extension
file size
HTTP completion
year
selected scrape date
```

### Step 3 — Extract / normalize

```text
ZIP → CSV
JSON.GZ → streaming JSON
```

### Step 4 — Convert to Parquet

```text
raw → silver Parquet
```

### Step 5 — Profile each source

Generate:

```text
row count
column count
distinct project IDs
null rates
duplicate project IDs
```

### Step 6 — Reconcile sources

Calculate overlap between:

```text
Web Robots
Kaggle Kemical 2016
Kaggle Kemical 2018
MasterKickstarter
```

### Step 7 — Build facts and dimensions

Create:

```text
Fact_Project
Fact_Project_Snapshot
Dim_Project
Dim_Date
Dim_Category
Dim_Location
Dim_Currency
```

### Step 8 — Connect Power BI

Use the Parquet connector for curated outputs where appropriate. Power BI supports Parquet import. citeturn314009search6

### Step 9 — Model

Build one-to-many relationships from dimensions into facts.

### Step 10 — Create measures

Use explicit DAX measures.

### Step 11 — QA

Validate:

```text
unique project count
success rate
funding totals
source overlaps
duplicate count
null keys
relationship cardinality
```

### Step 12 — Build issue-analysis pages

Recommended report pages:

```text
01 Executive Overview
02 Campaign Success & Failure
03 Funding & Goal Setting
04 Category Performance
05 Geography
06 Time / Snapshot Trends
07 Project Detail
08 Data Quality & Source Audit
```

---

# 27. Recommended Power BI Report Narrative

The report should tell a decision-oriented story rather than display disconnected visuals.

```text
Portfolio
   ↓
Success / Failure
   ↓
Funding performance
   ↓
Goal-setting behavior
   ↓
Category differences
   ↓
Geographic differences
   ↓
Temporal changes
   ↓
Root-cause hypotheses
   ↓
Recommended action
```

Each page should answer one business question.

---

# 28. Data Quality Page

Create a dedicated technical QA page for the analytics-engineering portfolio.

Display:

```text
Total source rows
Distinct projects
Duplicate rows
Null project IDs
Conflicting source values
Projects covered by Web Robots
Projects covered only by Kaggle
Latest snapshot date
Data refresh timestamp
```

This page is useful because the project's real challenge is not merely building charts; it is proving that the analytical numbers are trustworthy.

---

# 29. What Counts as a Duplicate?

Use these definitions consistently.

### Exact duplicate

Same:

```text
project_id
snapshot_date
source_system
```

with repeated rows.

→ **Remove.**

### Multi-category Web Robots duplicate

Same:

```text
project_id
snapshot_date
```

appears more than once because the crawler reached the project through multiple categories.

→ **Deduplicate at project snapshot grain.**

### Cross-year observation

Same:

```text
project_id
```

but different:

```text
snapshot_date
```

→ **Keep.**

### Cross-source overlap

Same:

```text
project_id
```

in Web Robots and Kaggle.

→ **Audit and reconcile; do not count as two projects.**

### Different project with similar name

Same/similar:

```text
project_name
```

but different ID.

→ **Keep as separate projects.**

---

# 30. Important Historical Coverage Limitation

Web Robots states that from April 2015 Kickstarter began limiting how many projects users could view within a single category. Web Robots therefore cannot guarantee that a single scrape captures the complete historical universe for that period; recent and active projects are always included according to their note. citeturn688018view0

This limitation must appear in the project's documentation.

Do not write:

> “The Web Robots dataset contains every Kickstarter project ever created.”

Use:

> “The Web Robots archive provides historical Kickstarter crawl snapshots, but historical coverage is subject to source-platform visibility limits and the crawler's collection methodology.”

---

# 31. JSON Handling

Web Robots says that from December 2015 the JSON output is JSON Streaming format. citeturn688018view0

Do not use:

```python
json.load(file)
```

for a very large historical JSON file.

Use streaming processing:

```python
import gzip
import orjson

with gzip.open(path, "rb") as f:
    for line in f:
        if not line.strip():
            continue

        record = orjson.loads(line)
        # transform record
```

Then write directly to Parquet using batches.

For large files, batch rather than accumulating every record in one giant Python list.

---

# 32. Performance Philosophy

The goal is not:

> “Make Power BI do everything.”

The goal is:

```text
Python / DuckDB
    = heavy ingestion + parsing + reconciliation

Power Query
    = governed shaping + reusable M transformations

Power BI / VertiPaq
    = semantic modeling + interactive analytics

DAX
    = business logic + measures
```

Microsoft's guidance emphasizes minimizing expensive Power Query processing, using appropriate source preparation, and designing a star schema for analytical models. citeturn314009search0turn314009search1

---

# 33. Final Architecture Checklist

Before calling the project complete, verify all of the following.

### Download layer

- [ ] Latest scrape per year selected automatically.
- [ ] CSV preferred.
- [ ] JSON used only when CSV is unavailable for the selected year/scrape.
- [ ] No CSV + JSON duplication for one scrape.
- [ ] Resume support works.
- [ ] File size is verified.
- [ ] Download manifest exists.

### Source layer

- [ ] Raw files remain unchanged.
- [ ] Source lineage exists.
- [ ] Snapshot/release metadata exists.
- [ ] Source schemas are profiled.

### Deduplication

- [ ] Project ID is the business key.
- [ ] Same project across years is retained as a historical observation.
- [ ] Same project within one snapshot is deduplicated.
- [ ] Cross-source overlaps are measured.
- [ ] No blind append of overlapping datasets.

### Transformation

- [ ] Heavy transformations occur upstream where practical.
- [ ] Parquet silver/gold files are generated.
- [ ] Power Query references curated outputs rather than raw archives.
- [ ] M code is modular and parameterized.
- [ ] `Table.Buffer` is not used as a blanket performance workaround.

### Semantic model

- [ ] Fact tables have documented grain.
- [ ] Dimensions are unique on the one side.
- [ ] Relationships are one-to-many wherever possible.
- [ ] Text is pushed toward dimensions where appropriate.
- [ ] Explicit DAX measures are used for business metrics.

### Analytics

- [ ] Success/failure analysis exists.
- [ ] Goal-setting analysis exists.
- [ ] Category analysis exists.
- [ ] Geography analysis exists.
- [ ] Temporal/snapshot analysis exists.
- [ ] Source/data-quality analysis exists.
- [ ] Findings distinguish correlation from causation.

---

# 34. Source References

### Web Robots

<https://webrobots.io/kickstarter-datasets/>

### Kaggle — MasterKickstarter

<https://www.kaggle.com/wood2174/mapkickstarter>

### Kaggle — Kickstarter Projects

<https://www.kaggle.com/datasets/kemical/kickstarter-projects>

### Microsoft Power BI — Star Schema

<https://learn.microsoft.com/power-bi/guidance/star-schema>

### Microsoft Power Query — Best Practices

<https://learn.microsoft.com/en-us/power-query/best-practices>

### Microsoft Power Query — Query Folding

<https://learn.microsoft.com/en-us/power-query/power-query-folding>

### Microsoft Power Query — Referenced Queries

<https://learn.microsoft.com/en-us/power-bi/guidance/power-query-referenced-queries>

### Microsoft Power Query — Parquet Connector

<https://learn.microsoft.com/en-us/power-query/connectors/parquet>

---

# 35. Project Principle

> **Do not optimize for the biggest dataset. Optimize for the most trustworthy analytical grain.**

For this Kickstarter project, the key engineering insight is that the datasets are not simply several copies of a CSV. They represent different **source systems, historical snapshots, schemas, coverage periods, and collection methods**.

The finished Power BI model should make that complexity explicit, control duplication deliberately, preserve lineage, and turn the resulting data into defensible analysis of Kickstarter success and failure.
