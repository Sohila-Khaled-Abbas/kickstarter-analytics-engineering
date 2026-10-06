# Phase 3: Dimensional Modeling & Fact Creation

**Objective:** Build the finalized Galaxy Schema by creating distinct Conformed Dimensions and granular Fact tables.

## 1. Conformed Dimensions
Create these queries by referencing your `02 Staging` queries, appending them together, keeping only the relevant columns, removing duplicates, and adding an Index Column starting from 1 (the Surrogate Key).

*   **`Dim_Project`:** `ProjectKey` (Index), `ProjectID`, `ProjectName`, `Slug`, `Blurb`, `ProjectURL`, `LaunchDate`, `DeadlineDate`, `CampaignDurationDays`. *(Do not include volatile measures like PledgedUSD here).*
*   **`Dim_Category`:** `CategoryKey` (Index), `MainCategory`, `Subcategory`.
*   **`Dim_Location`:** `LocationKey` (Index), `CountryCode`, `CountryName`, `State`, `City`, `Latitude`, `Longitude`.
*   **`Dim_Currency`:** `CurrencyKey` (Index), `CurrencyCode`, `CurrencySymbol`.
*   **`Dim_Status`:** `StatusKey` (Index), `Status` (successful, failed, live, etc.), `OutcomeGroup`, `IsCompleted` (1/0), `IsSuccessful` (1/0).

## 2. Dim_Date (Built in DAX)
Create your Date dimension directly in the Data view using DAX:

```dax
Dim_Date =
ADDCOLUMNS(
    CALENDAR(DATE(2009,1,1), DATE(2026,12,31)),
    "DateKey", VALUE(FORMAT([Date], "YYYYMMDD")),
    "Year", YEAR([Date]),
    "MonthNumber", MONTH([Date]),
    "MonthName", FORMAT([Date], "MMMM"),
    "YearMonth", FORMAT([Date], "YYYY-MM"),
    "Quarter", "Q" & FORMAT([Date], "Q"),
    "DayOfWeek", WEEKDAY([Date], 2),
    "DayName", FORMAT([Date], "dddd")
)
```

## 3. Fact Tables

### Fact_Campaign (The Static Master)
*   **Grain:** 1 row per unique `ProjectID`.
*   **Deduplication:** Sort by source priority and recency, buffer the table, and `Table.Distinct` by `ProjectID`.
*   **Columns:** `ProjectKey`, `CategoryKey`, `LocationKey`, `CurrencyKey`, `StatusKey`, `LaunchDateKey`, `GoalUSD`, `PledgedUSD`, `BackerCount`.

### Fact_CampaignSnapshot (The WebRobots Time-Series)
*   **Grain:** 1 row per `ProjectID` + `SnapshotDate`.
*   **Deduplication:** Group by `ProjectID` AND `SnapshotDateKey`.
*   **Columns:** `ProjectKey`, `SnapshotDateKey`, `CategoryKey`, `LocationKey`, `StatusKey`, `GoalUSD`, `PledgedUSD`, `BackerCount`, `StaffPickFlag`.

### Geographic Fact Tables
*   **`Fact_CityMetrics` / `Fact_StateMetrics` / `Fact_CountyMetrics`:** Derived from `Mapping.csv`, `County.csv`, and the extracted geographic columns of `MasterKickstarter`.
*   **Columns:** `LocationKey`, `DateKey` (if applicable), `TotalCityBackers`, `MeanCampaignUSD`, `MedianBackers`.