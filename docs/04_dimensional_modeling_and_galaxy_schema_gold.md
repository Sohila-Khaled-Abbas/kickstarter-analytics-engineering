# 04 — Dimensional Modeling & Galaxy Schema (Gold) Guide

## Galaxy Schema (Fact Constellation) Design Blueprint

The **Gold Layer** is the final, user-facing analytical model loaded into Power BI's in-memory columnar database (VertiPaq). In this layer, queries switch from `Enable Load = False` to **`Enable Load = True`**.

---

## 1. Why a Single Star Schema is Insufficient

A conventional Star Schema centers around a single Fact table. However, our Kickstarter dataset spans multiple distinct business entities and grains:

1. **Static Campaign Master**: One row per unique campaign, capturing final outcome and total raised.
2. **Longitudinal Crawl Snapshots**: Multiple observations per campaign across WebRobots monthly crawls (2014–2026), capturing funding progression.
3. **Geographic Demographics & Benchmarks**: Aggregate metrics per City, US County (`County.csv`), and US State (`Mapping.csv`).

If an analytics engineer attempts to cram city population and county statistics into `Fact_Campaign`, any visual that slices by Category will multiply county population numbers by thousands of campaigns, corrupting aggregations.

### The Solution: Galaxy Schema (Fact Constellation)
We implement a **Galaxy Schema**, where multiple Fact tables share a unified suite of **Conformed Dimensions**:

```mermaid
graph TD
    subgraph Dimensions["🌌 Shared Conformed Dimensions"]
        D_Date["Dim_Date<br/>(DAX Calendar 2009-2026)"]
        D_Cat["Dim_Category<br/>(CategoryKey)"]
        D_Loc["Dim_Location<br/>(LocationKey)"]
        D_Curr["Dim_Currency<br/>(CurrencyKey)"]
        D_Stat["Dim_Status<br/>(StatusKey)"]
        D_Proj["Dim_Project<br/>(ProjectKey)"]
    end

    subgraph Facts["📊 Fact Constellation (Multiple Grains)"]
        F_Camp[["Fact_Campaign<br/>Grain: 1 row / Project"]]
        F_Snap[["Fact_CampaignSnapshot<br/>Grain: 1 row / Project / Scrape"]]
        F_City[["Fact_CityMetrics<br/>Grain: 1 row / City"]]
        F_State[["Dim_State_Metrics<br/>Grain: 1 row / US State"]]
        F_County[["Dim_County_Metrics<br/>Grain: 1 row / US County"]]
    end

    %% Fact_Campaign Links
    D_Date -->|LaunchDateKey (Active)| F_Camp
    D_Date -.->|DeadlineDateKey (Inactive)| F_Camp
    D_Cat --> F_Camp
    D_Loc --> F_Camp
    D_Curr --> F_Camp
    D_Stat --> F_Camp
    D_Proj --> F_Camp

    %% Fact_CampaignSnapshot Links
    D_Date -->|SnapshotDateKey (Active)| F_Snap
    D_Cat --> F_Snap
    D_Curr --> F_Snap
    D_Stat --> F_Snap
    D_Proj --> F_Snap

    %% Geo Metric Links
    D_Loc --> F_City
    D_Loc --> F_State
    D_Loc --> F_County
```

---

## 2. Table Grains & Schema Specifications

### Conformed Dimensions

#### 1. `Dim_Project`
- **Grain**: 1 row per unique Kickstarter project.
- **Attributes**: `ProjectKey` (PK, Int64), `ProjectID` (Natural Key, Int64), `ProjectName`, `ProjectSlug`, `Blurb`, `Source_System`.

#### 2. `Dim_Category`
- **Grain**: 1 row per Category + Subcategory combination.
- **Attributes**: `CategoryKey` (PK, Int64), `Category`, `Subcategory`.

#### 3. `Dim_Location`
- **Grain**: 1 row per unique City + State + Country combination.
- **Attributes**: `LocationKey` (PK, Int64), `CountryCode`, `CountryName`, `State`, `County`, `City`, `Latitude`, `Longitude`.

#### 4. `Dim_Currency`
- **Grain**: 1 row per ISO currency code.
- **Attributes**: `CurrencyKey` (PK, Int64), `CurrencyCode`, `CurrencySymbol`.

#### 5. `Dim_Status`
- **Grain**: 1 row per campaign state.
- **Attributes**: `StatusKey` (PK, Int64), `ProjectStatus`, `StatusGroup` ('Funded', 'In Progress', 'Unfunded'), `IsCompleted` (1/0), `IsSuccessful` (1/0).

#### 6. `Dim_Date` (DAX-Generated)
- **Grain**: 1 row per calendar day from Jan 1, 2009 to Dec 31, 2026.
- **Attributes**: `DateKey` (PK, `YYYYMMDD`, Int64), `Date`, `Year`, `MonthNumber`, `MonthName`, `YearMonth`, `Quarter`, `DayOfWeek`, `DayName`, `IsWeekend`.

---

### Fact Tables

#### 1. `Fact_Campaign` (Core Fact)
- **Grain**: 1 row per unique project (Canonical portfolio record).
- **Foreign Keys**:
  - `ProjectKey` → `Dim_Project[ProjectKey]`
  - `CategoryKey` → `Dim_Category[CategoryKey]`
  - `LocationKey` → `Dim_Location[LocationKey]`
  - `CurrencyKey` → `Dim_Currency[CurrencyKey]`
  - `StatusKey` → `Dim_Status[StatusKey]`
  - `LaunchDateKey` → `Dim_Date[DateKey]` (Active)
  - `DeadlineDateKey` → `Dim_Date[DateKey]` (Inactive)
- **Measures / Metrics**: `GoalUSD`, `PledgedUSD`, `GoalLocal`, `PledgedLocal`, `BackerCount`, `CampaignDurationDays`, `GoalAchievementPct`, `PledgePerBacker`.

#### 2. `Fact_CampaignSnapshot` (Longitudinal Fact)
- **Grain**: 1 row per project per WebRobots crawl snapshot.
- **Foreign Keys**: `ProjectKey`, `CategoryKey`, `CurrencyKey`, `StatusKey`, `SnapshotDateKey` → `Dim_Date[DateKey]`.
- **Measures / Metrics**: `GoalUSD`, `PledgedUSD`, `BackerCount`.

#### 3. `Fact_CityMetrics`
- **Grain**: 1 row per city.
- **Attributes / Metrics**: `LocationKey`, `CityPopulation`, `CityAllTimeBackers`, `MeanPledgeCity`.

#### 4. `Dim_State_Metrics` & `Dim_County_Metrics`
- Loaded from `Mapping.csv` and `County.csv` providing regional benchmark baselines.

---

## 3. Creating the Enterprise `Dim_Date` Table in DAX

To support robust Time Intelligence and multi-date role-playing relationships without relying on Power BI's bloated auto-date/time hierarchy:

```dax
Dim_Date = 
VAR MinDate = DATE(2009, 1, 1)
VAR MaxDate = DATE(2026, 12, 31)
RETURN
ADDCOLUMNS(
    CALENDAR(MinDate, MaxDate),
    "DateKey", VALUE(FORMAT([Date], "YYYYMMDD")),
    "Year", YEAR([Date]),
    "MonthNumber", MONTH([Date]),
    "MonthName", FORMAT([Date], "MMMM"),
    "MonthShort", FORMAT([Date], "MMM"),
    "YearMonth", FORMAT([Date], "YYYY-MM"),
    "Quarter", "Q" & FORMAT([Date], "Q"),
    "YearQuarter", FORMAT([Date], "YYYY") & " Q" & FORMAT([Date], "Q"),
    "DayOfMonth", DAY([Date]),
    "DayOfWeekNumber", WEEKDAY([Date], 2), -- 1 = Monday, 7 = Sunday
    "DayName", FORMAT([Date], "dddd"),
    "DayShort", FORMAT([Date], "ddd"),
    "IsWeekend", IF(WEEKDAY([Date], 2) IN {6, 7}, 1, 0)
)
```

### Mandatory Sort By Column Rules:
- Select `MonthName` → Set **Sort by column** to `MonthNumber`.
- Select `MonthShort` → Set **Sort by column** to `MonthNumber`.
- Select `YearQuarter` → Set **Sort by column** to `DateKey`.
- Mark as Date Table: Right-click `Dim_Date` → **Mark as date table** → Select `[Date]`.

---

## 4. Relationship Architecture & Cardinality Rules

In Power BI Model View, configure relationships adhering strictly to Kimball enterprise standards:

| From Table (Fact) | Foreign Key | To Table (Dim) | Primary Key | Cardinality | Cross Filter | Active State |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Fact_Campaign` | `ProjectKey` | `Dim_Project` | `ProjectKey` | Many-to-One (*:1) | Single | **Active** |
| `Fact_Campaign` | `CategoryKey` | `Dim_Category` | `CategoryKey` | Many-to-One (*:1) | Single | **Active** |
| `Fact_Campaign` | `LocationKey` | `Dim_Location` | `LocationKey` | Many-to-One (*:1) | Single | **Active** |
| `Fact_Campaign` | `CurrencyKey` | `Dim_Currency` | `CurrencyKey` | Many-to-One (*:1) | Single | **Active** |
| `Fact_Campaign` | `StatusKey` | `Dim_Status` | `StatusKey` | Many-to-One (*:1) | Single | **Active** |
| `Fact_Campaign` | `LaunchDateKey` | `Dim_Date` | `DateKey` | Many-to-One (*:1) | Single | **Active** |
| `Fact_Campaign` | `DeadlineDateKey`| `Dim_Date` | `DateKey` | Many-to-One (*:1) | Single | **Inactive** |
| `Fact_CampaignSnapshot` | `ProjectKey` | `Dim_Project` | `ProjectKey` | Many-to-One (*:1) | Single | **Active** |
| `Fact_CampaignSnapshot` | `CategoryKey`| `Dim_Category` | `CategoryKey` | Many-to-One (*:1) | Single | **Active** |
| `Fact_CampaignSnapshot` | `SnapshotDateKey` | `Dim_Date` | `DateKey` | Many-to-One (*:1) | Single | **Active** |

> [!CAUTION]
> **Strict Modeling Commandments**:
> 1. **Never use Bi-Directional filtering** (`Both`). It causes ambiguous filter paths and severe performance degradation.
> 2. **Never create Fact-to-Fact relationships**. `Fact_Campaign` and `Fact_CampaignSnapshot` must communicate exclusively through shared dimensions (`Dim_Project`, `Dim_Category`, `Dim_Date`).
> 3. **Hide All Surrogate Keys**: Right-click every foreign key column (`*Key`) in Fact tables and select **Hide in report view**. End users should only filter using descriptive text fields in Dimension tables.
