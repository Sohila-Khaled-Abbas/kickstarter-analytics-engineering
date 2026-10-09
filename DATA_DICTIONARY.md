# Enterprise Data Dictionary

## Kickstarter Analytics Engineering Semantic Model

This document serves as the canonical data catalog and dictionary for the **Kickstarter Analytics Engineering Platform**. It details every entity, grain, attribute, data type, nullability, and business definition across all architectural layers.

---

## 1. Conformed Dimensions (`04_Dimensions`)

### A. `Dim_Project`
- **Business Description**: Stores immutable project identification and creative attributes.
- **Table Grain**: One row per unique Kickstarter project.
- **Storage Type**: Direct VertiPaq Columnar Table.

| Column Name | Data Type | Nullable | Key Type | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- |
| `ProjectKey` | `Int64` | No | **PK** | Surrogate integer key generated via index column. Used for all fact joins. |
| `ProjectID` | `Int64` | No | **NK** | Natural Kickstarter platform project ID. Unique across all rows. |
| `ProjectName` | `Text` | No | None | Cleaned, whitespace-trimmed title of the campaign. |
| `ProjectSlug` | `Text` | Yes | None | Web URL slug identifier on Kickstarter.com. |
| `Blurb` | `Text` | Yes | None | Short creative pitch / summary blurb written by the creator. |
| `Source_System` | `Text` | No | None | Origin source granting canonical authority ('WebRobots', 'Kaggle_2018', etc.). |

---

### B. `Dim_Category`
- **Business Description**: Two-tier hierarchical classification of projects.
- **Table Grain**: One row per unique Category and Subcategory combination.

| Column Name | Data Type | Nullable | Key Type | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- |
| `CategoryKey` | `Int64` | No | **PK** | Surrogate integer primary key. |
| `Category` | `Text` | No | None | Top-level creative vertical ('Games', 'Technology', 'Design', 'Film & Video'). |
| `Subcategory` | `Text` | No | None | Granular niche vertical ('Tabletop Games', 'Web', 'Product Design', etc.). |

---

### C. `Dim_Location`
- **Business Description**: Geographic hierarchy extracted from MasterKickstarter and Kaggle country ISOs.
- **Table Grain**: One row per unique geographic location (City, State, Country).

| Column Name | Data Type | Nullable | Key Type | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- |
| `LocationKey` | `Int64` | No | **PK** | Surrogate integer primary key. |
| `CountryCode` | `Text` | Yes | None | ISO 3166-1 alpha-2 country code ('US', 'GB', 'CA', 'AU', etc.). |
| `CountryName` | `Text` | Yes | None | Full localized country name. |
| `State` | `Text` | Yes | None | State, province, or region name. |
| `County` | `Text` | Yes | None | US County name (aligned with `County.csv`). |
| `City` | `Text` | Yes | None | Municipal city name. |
| `Latitude` | `Double` | Yes | None | Geospatial coordinate (WGS84). |
| `Longitude` | `Double` | Yes | None | Geospatial coordinate (WGS84). |

---

### D. `Dim_Currency`
- **Business Description**: Currencies used for campaign pledge collection.
- **Table Grain**: One row per currency code.

| Column Name | Data Type | Nullable | Key Type | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- |
| `CurrencyKey` | `Int64` | No | **PK** | Surrogate integer primary key. |
| `CurrencyCode` | `Text` | No | None | ISO 4217 currency code ('USD', 'GBP', 'EUR', 'CAD', 'AUD', etc.). |
| `CurrencySymbol` | `Text` | Yes | None | Display currency symbol ('$', '£', '€', 'CA$'). |

---

### E. `Dim_Status`
- **Business Description**: Categorization of campaign completion states.
- **Table Grain**: One row per campaign state.

| Column Name | Data Type | Nullable | Key Type | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- |
| `StatusKey` | `Int64` | No | **PK** | Surrogate integer primary key. |
| `ProjectStatus` | `Text` | No | None | Canonical status string ('Successful', 'Failed', 'Canceled', 'Live', 'Suspended'). |
| `StatusGroup` | `Text` | No | None | High-level business group ('Funded', 'Unfunded', 'In Progress'). |
| `IsCompleted` | `Int64` | No | None | Boolean indicator (1 = campaign cutoff reached, 0 = active/live). |
| `IsSuccessful` | `Int64` | No | None | Boolean indicator (1 = reached 100%+ funding goal, 0 = did not fund). |

---

### F. `Dim_Date`
- **Business Description**: Enterprise calendar table covering 2009–2026.
- **Table Grain**: One row per calendar day.

| Column Name | Data Type | Nullable | Key Type | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- |
| `DateKey` | `Int64` | No | **PK** | Integer date key formatted as `YYYYMMDD` (e.g., 20161231). |
| `Date` | `Date` | No | None | Standard date value. |
| `Year` | `Int64` | No | None | Calendar year (2009–2026). |
| `MonthNumber` | `Int64` | No | None | Calendar month number (1–12). |
| `MonthName` | `Text` | No | None | Full month name ('January', 'February', etc.). Sorted by `MonthNumber`. |
| `YearMonth` | `Text` | No | None | Formatted year and month (`YYYY-MM`). |
| `Quarter` | `Text` | No | None | Formatted quarter ('Q1', 'Q2', 'Q3', 'Q4'). |
| `DayOfWeek` | `Int64` | No | None | Day index (1 = Monday, 7 = Sunday). |
| `IsWeekend` | `Int64` | No | None | Indicator (1 = Saturday or Sunday, 0 = Weekday). |

---

## 2. Fact Tables (`05_Facts`)

### A. `Fact_Campaign`
- **Business Description**: Core portfolio fact capturing final campaign performance and funding outcome.
- **Table Grain**: Exactly one row per unique Kickstarter project.

| Column Name | Data Type | Key Type | Description & Business Rules |
| :--- | :--- | :--- | :--- |
| `ProjectKey` | `Int64` | **FK** | Joins to `Dim_Project[ProjectKey]`. |
| `CategoryKey` | `Int64` | **FK** | Joins to `Dim_Category[CategoryKey]`. |
| `LocationKey` | `Int64` | **FK** | Joins to `Dim_Location[LocationKey]`. |
| `CurrencyKey` | `Int64` | **FK** | Joins to `Dim_Currency[CurrencyKey]`. |
| `StatusKey` | `Int64` | **FK** | Joins to `Dim_Status[StatusKey]`. |
| `LaunchDateKey` | `Int64` | **FK (Active)** | Joins to `Dim_Date[DateKey]`. Active date relationship. |
| `DeadlineDateKey` | `Int64` | **FK (Inactive)** | Joins to `Dim_Date[DateKey]`. Activated via `USERELATIONSHIP`. |
| `GoalUSD` | `Currency` | None | Target funding goal normalized to USD. |
| `PledgedUSD` | `Currency` | None | Total funds pledged normalized to USD. |
| `GoalLocal` | `Currency` | None | Target goal in native currency. |
| `PledgedLocal` | `Currency` | None | Total pledged in native currency. |
| `BackerCount` | `Int64` | None | Total count of individuals who backed the campaign. |
| `CampaignDurationDays` | `Int64` | None | Duration in integer days (`DeadlineDate - LaunchDate`). |
| `GoalAchievementPct` | `Percentage` | None | Pre-calculated funding ratio (`PledgedUSD / GoalUSD`). |
| `PledgePerBacker` | `Currency` | None | Average contribution (`PledgedUSD / BackerCount`). |

---

### B. `Fact_CampaignSnapshot`
- **Business Description**: Longitudinal time-series observations extracted from recurring WebRobots crawls (2014–2026).
- **Table Grain**: One row per project per WebRobots scrape event.

| Column Name | Data Type | Key Type | Description & Business Rules |
| :--- | :--- | :--- | :--- |
| `ProjectKey` | `Int64` | **FK** | Joins to `Dim_Project[ProjectKey]`. |
| `CategoryKey` | `Int64` | **FK** | Joins to `Dim_Category[CategoryKey]`. |
| `CurrencyKey` | `Int64` | **FK** | Joins to `Dim_Currency[CurrencyKey]`. |
| `StatusKey` | `Int64` | **FK** | Joins to `Dim_Status[StatusKey]`. |
| `SnapshotDateKey` | `Int64` | **FK (Active)** | Date the web crawler scraped the campaign record. |
| `GoalUSD` | `Currency` | None | Target funding goal in USD at scrape time. |
| `PledgedUSD` | `Currency` | None | Cumulative pledged USD recorded at scrape time. |
| `BackerCount` | `Int64` | None | Cumulative backer count recorded at scrape time. |

---

### C. `Fact_CityMetrics`
- **Business Description**: Demographic and localized Kickstarter adoption aggregates.
- **Table Grain**: One row per municipal city.

| Column Name | Data Type | Key Type | Description & Business Rules |
| :--- | :--- | :--- | :--- |
| `LocationKey` | `Int64` | **FK** | Joins to `Dim_Location[LocationKey]`. |
| `CityPopulation` | `Int64` | None | Census population recorded in MasterKickstarter. |
| `CityAllTimeBackers`| `Int64` | None | Cumulative all-time backers residing in this city. |
| `MeanPledgeCity` | `Currency` | None | Average pledge amount for projects originating in this city. |

---

### D. `Dim_State_Metrics` & `Dim_County_Metrics`
- **Business Description**: Benchmark reference tables loaded directly from `Mapping.csv` and `County.csv`.
- **Grain**: One row per US State / One row per US County.
- **Attributes**:
  - `Dim_State_Metrics`: `State`, `Mean Campaign USD`, `Projects Per`, `Mean Bakers`, `Total Pledged`, `Total Backers`, `Mean Days Building`, `Median Percent of Goal`.
  - `Dim_County_Metrics`: `subregion` (County), `region` (State), `TotalBackers`, `MeanBackers`, `MedianBackers`, `MeanUSD`, `TotalUSD`, `MedianUSD`.
