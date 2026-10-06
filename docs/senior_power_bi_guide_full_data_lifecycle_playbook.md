**Do not collapse all three datasets into one “latest project” fact.**  
WebRobots is a recurring snapshot source, so deduplicating it down to one row per project destroys the historical behavior you actually want to analyze. WebRobots says its Kickstarter crawl has been run monthly since March 2016, with dated snapshots available through 2026. [Web Scraping Service](https://webrobots.io/kickstarter-datasets/)

For this project, a **galaxy schema / fact constellation** is much stronger: multiple fact tables sharing the same conformed dimensions.

The source landscape also genuinely supports that approach. The `kemical/kickstarter-projects` dataset has the classic 15-column campaign structure—ID, name, category/subcategory, currency, dates, goal, pledged, state, backers, country, and USD conversion fields. [GitHub](https://github.com/ayoubabozer/kickstarter?utm_source=chatgpt.com) The `wood2174/mapkickstarter` dataset is broader: the referenced project repository describes `MasterKickstarter.csv` as about 99,000 projects with 57 attributes, including geographic and campaign characteristics. [GitHub](https://github.com/LeGriffon/Kickstarters_Data_Analysis?utm_source=chatgpt.com) WebRobots adds a much richer monthly snapshot structure including fields such as `id`, `name`, `goal`, `pledged`, `state`, `country`, `currency`, `deadline`, `state_changed_at`, `created_at`, `launched_at`, `backers_count`, `static_usd_rate`, `usd_pledged`, `location`, `category`, `profile`, and URLs. [RStudio Pubs](https://rstudio-pubs-static.s3.amazonaws.com/337307_590d8c5747e94e398f01ba5f27fad781.html?utm_source=chatgpt.com)

---

# 1. The architecture I recommend

Build this:

```text
                         ┌──────────────────┐
                         │    Dim_Date      │
                         └────────┬─────────┘
                                  │
              ┌───────────────────┼────────────────────┐
              │                   │                    │
              ▼                   ▼                    ▼
      ┌──────────────┐    ┌──────────────┐     ┌──────────────┐
      │ Dim_Category │    │ Dim_Location │     │ Dim_Currency │
      └──────┬───────┘    └──────┬───────┘     └──────┬───────┘
             │                   │                    │
             │                   │                    │
             ▼                   ▼                    ▼
        ┌────────────────────────────────────────────────────┐
        │             Fact_Campaign                           │
        │  grain = 1 row / unique Kickstarter project        │
        └────────────────────────────────────────────────────┘
             ▲                   ▲                    ▲
             │                   │                    │
             │                   │                    │
        ┌────┴────────┐     ┌────┴────────────┐
        │ Dim_Project │     │ Dim_Status      │
        └─────────────┘     └─────────────────┘


                         ┌────────────────────────┐
                         │ Fact_CampaignSnapshot  │
                         │ grain = project ×      │
                         │ snapshot date          │
                         └────────────────────────┘
                                  ▲
                                  │
                       shares all conformed dims


                         ┌────────────────────────┐
                         │ Fact_CityMetrics        │
                         │ grain = city × period  │
                         └────────────────────────┘
                                  ▲
                                  │
                         ┌──────────────────┐
                         │ Fact_GeoMetrics   │
                         │ state/county grain│
                         └──────────────────┘
```

That is a **galaxy** because several fact tables are connected to the same reusable dimensions.

Microsoft's modeling guidance specifically recommends dimensions for filtering/grouping and facts for summarization, with one-to-many relationships from dimensions to facts. It also recommends avoiding direct fact-to-fact many-to-many relationships. [Microsoft Learn](https://learn.microsoft.com/power-bi/guidance/star-schema?utm_source=chatgpt.com)

---

# 2. Your Power Query folder structure

I would use:

```text
00 Parameters
│
├── pDataFolder
├── pWebRobotsFolder
└── pDefaultCurrency

01 Sources
│
├── Src_Kaggle_2016
├── Src_Kaggle_2018
├── Src_MasterKickstarter
├── Src_WebRobots
├── Src_Mapping
└── Src_County

02 Staging
│
├── Stg_Kaggle_2016
├── Stg_Kaggle_2018
├── Stg_MasterKickstarter
├── Stg_WebRobots
├── Stg_Mapping
└── Stg_County

03 Conformed
│
├── Conformed_Project
├── Conformed_Category
├── Conformed_Location
├── Conformed_Currency
└── Conformed_Status

04 Dimensions
│
├── Dim_Date
├── Dim_Project
├── Dim_Category
├── Dim_Location
├── Dim_Currency
└── Dim_Status

05 Facts
│
├── Fact_Campaign
├── Fact_CampaignSnapshot
├── Fact_CityMetrics
├── Fact_StateMetrics
└── Fact_CountyMetrics

99 QA
│
├── QA_DuplicateProjects
├── QA_OrphanProjects
├── QA_OrphanCategories
├── QA_OrphanLocations
├── QA_NullKeys
├── QA_DateErrors
└── QA_ValueChecks

Measures
└── Measures
```

Your uploaded playbook already uses the layered `00 Parameters` → `01 Sources` → `02 Staging` → `03 Conformed` → `04 Dimensions` → `05 Facts` structure, with loading disabled on the preparation layers. senior_power_bi_guide_full_data…

Keep that structure. The main thing we are changing is **what the conformed/fact layers actually mean**.

---

# 3. First: establish the grain

This is the most important step before touching Power Query.

Write this down in your project documentation:

| Table | Grain |
| --- | --- |
| `Fact_Campaign` | One row per unique Kickstarter project |
| `Fact_CampaignSnapshot` | One row per project per WebRobots snapshot |
| `Fact_CityMetrics` | One row per city per defined period/source |
| `Fact_StateMetrics` | One row per state per defined period/source |
| `Fact_CountyMetrics` | One row per county per defined period/source |

That prevents the #1 Power BI modeling mistake: mixing different grains inside one fact table. Microsoft explicitly recommends that fact tables load at a consistent grain. [Microsoft Learn](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema?WT.mc_id=AI-MVP-5004077\&utm_source=chatgpt.com)

---

# 4. Source 1 — Kaggle `kemical/kickstarter-projects`

This is your historical campaign dataset.

The well-known 2018 file has:

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

The published dataset structure confirms those 15 fields. [niser.ac.in](https://www.niser.ac.in/~smishra/teach/cs460/2020/lectures/lec14/KickstarterExample.html?utm_source=chatgpt.com)

## Staging transformations

Create:

`Stg_Kaggle_2018`

### Step 1 — Rename

```text
ID                  → ProjectID
name                → ProjectName
category            → Subcategory
main_category       → Category
currency            → CurrencyCode
deadline            → DeadlineDateTime
goal                → GoalLocal
launched            → LaunchDateTime
pledged             → PledgedLocal
state               → ProjectStatus
backers             → BackerCount
country             → CountryCode
usd pledged         → PledgedUSD_KS
usd_pledged_real    → PledgedUSD
usd_goal_real       → GoalUSD
```

Notice that I would **not** casually rename `usd_pledged_real` to generic `pledged_usd` and forget its meaning. The source has different USD measures.

### Step 2 — Clean text

For every text column:

```powerquery
Text.Trim()
```

and preferably:

```powerquery
Text.Clean()
```

For status:

```powerquery
Text.Lower(Text.Trim([ProjectStatus]))
```

### Step 3 — Correct types

Use:

```text
ProjectID           Whole Number / preferably Int64
ProjectName         Text
Subcategory         Text
Category            Text
CurrencyCode        Text
DeadlineDateTime    Date/Time
GoalLocal           Decimal Number
LaunchDateTime      Date/Time
PledgedLocal        Decimal Number
ProjectStatus       Text
BackerCount         Whole Number
CountryCode         Text
PledgedUSD_KS       Decimal Number
PledgedUSD          Decimal Number
GoalUSD             Decimal Number
```

### Step 4 — Remove impossible records

Don't delete blindly.

Create flags:

```text
InvalidProjectID
InvalidGoal
InvalidLaunchDate
InvalidDeadline
```

rather than immediately deleting.

For example:

```powerquery
= Table.AddColumn(
    PreviousStep,
    "DurationDays",
    each Duration.Days([DeadlineDateTime] - [LaunchDateTime]),
    Int64.Type
)
```

Then:

```text
DurationDays < 0
GoalUSD < 0
PledgedUSD < 0
BackerCount < 0
```

should be QA exceptions.

### Step 5 — Feature engineering

Add:

```text
LaunchDate
LaunchYear
LaunchMonth
LaunchQuarter
DeadlineDate
CampaignDurationDays
FundingRatio
GoalAchievementPct
PledgePerBacker
```

Use:

```powerquery
FundingRatio =
if [GoalUSD] = null or [GoalUSD] = 0
then null
else [PledgedUSD] / [GoalUSD]
```

Do not divide by zero.

---

# 5. Kaggle 2016 needs special treatment

This one is slightly annoying.

The 2016 CSV is known to have encoding issues and can contain extra `Unnamed` columns; examples of the file show the fields through `usd pledged` plus empty unnamed columns. Windows-1252 is commonly required for that file. [Criskrus](https://criskrus.github.io/kaggle/06-data-cleaning/04-character-encodings/character-encodings.html?utm_source=chatgpt.com)

So for:

`Stg_Kaggle_2016`

do:

### Encoding

When reading the CSV, use Windows-1252 / code page 1252.

### Remove

```text
Unnamed: 13
Unnamed: 14
Unnamed: 15
Unnamed: 16
```

and any equivalent blank columns.

### Rename

```text
ID             → ProjectID
name           → ProjectName
category       → Subcategory
main_category  → Category
currency       → CurrencyCode
deadline       → DeadlineDateTime
goal           → GoalLocal
launched       → LaunchDateTime
pledged        → PledgedLocal
state          → ProjectStatus
backers        → BackerCount
country        → CountryCode
usd pledged    → PledgedUSD_KS
```

**Don't manufacture `GoalUSD` for 2016** unless you have a defensible exchange-rate field.

That is a subtle but important data-engineering decision.

Instead:

```text
GoalUSD = null
```

unless:

```text
CurrencyCode = "USD"
```

in which case:

```powerquery
if [CurrencyCode] = "USD" then [GoalLocal] else null
```

This prevents fake precision.

---

# 6. Source 2 — `MasterKickstarter.csv`

This source is different.

The exact `wood2174/mapkickstarter` dataset is described in a project using it as roughly **99,000 records and 57 attributes**, so it is not simply another copy of the 15-column Kaggle structure. [GitHub](https://github.com/LeGriffon/Kickstarters_Data_Analysis?utm_source=chatgpt.com)

Published work using the exact Master dataset shows fields such as:

```text
City
State
Longitude
Latitude
Categories
status
All_Time_Backers_city
Pledge_per_person
City_Pop
Days_spent_making_campign
Prct_goal
```

along with the campaign-level data. [GitHub](https://github.com/LeGriffon/Kickstarters_Data_Analysis?utm_source=chatgpt.com)

This dataset is where your **geographic analytical layer** becomes interesting.

## Staging approach

Don't immediately drop 50 columns.

First:

```text
Stg_MasterKickstarter
```

### Step 1

Normalize column names.

I recommend:

```text
Categories → Category
status     → ProjectStatus
City       → City
State      → State
```

etc.

### Step 2

Trim text.

Especially:

```text
City
State
Country
Category
Subcategory
ProjectStatus
```

### Step 3

Normalize states

For example:

```text
California
CALIFORNIA
california
```

must become one value.

Use:

```powerquery
Text.Proper(Text.Trim([State]))
```

But be careful with abbreviations like:

```text
CA
California
```

Those need a mapping table rather than `Text.Proper`.

### Step 4

Create geography hierarchy

Your location grain can become:

```text
Country
   ↓
State
   ↓
City
   ↓
Latitude / Longitude
```

### Step 5

Separate campaign and city data

This is critical.

Do **not** put:

```text
City_Pop
All_Time_Backers_city
Mean...
Median...
```

into every campaign row just because they arrived in the same CSV.

Those are geographic metrics.

Create:

`Fact_CityMetrics`

instead.

---

# 7. Source 3 — WebRobots

This is the most valuable source for the galaxy model.

WebRobots explicitly describes its dataset as a recurring crawl and publishes dated snapshots. [Web Scraping Service](https://webrobots.io/kickstarter-datasets/)

The structure is much richer than the Kaggle file. Published analysis of the WebRobots Kickstarter data shows fields including:

```text
id
name
blurb
goal
pledged
state
slug
country
currency
currency_symbol
deadline
state_changed_at
created_at
launched_at
staff_pick
is_starrable
backers_count
static_usd_rate
usd_pledged
converted_pledged_amount
current_currency
usd_type
spotlight
source_url
location
category
profile
urls
```

and notes that several fields are JSON/nested structures. [RStudio Pubs](https://rstudio-pubs-static.s3.amazonaws.com/337307_590d8c5747e94e398f01ba5f27fad781.html?utm_source=chatgpt.com)

This is exactly why it should become a **snapshot fact** rather than being treated like another static campaign table.

---

# 8. WebRobots fact design

Your final table:

`Fact_CampaignSnapshot`

should look roughly like:

```text
ProjectKey
SnapshotDateKey
LaunchDateKey
DeadlineDateKey
StateChangedDateKey
CategoryKey
LocationKey
CurrencyKey
StatusKey

GoalLocal
PledgedLocal
PledgedUSD
ConvertedPledgedAmount
BackerCount
StaticUSDRate

StaffPickFlag
SpotlightFlag
IsStarrableFlag
```

And:

```text
SnapshotDate
```

is derived from the WebRobots file/snapshot date—not from `launched_at`.

That distinction is huge.

Example:

```text
Project 123
2017-06 snapshot → pledged = 2,000
2017-07 snapshot → pledged = 5,500
2017-08 snapshot → pledged = 8,200
```

You now have a proper historical series.

---

# 9. DON'T use the previous deduplication logic on WebRobots

Your uploaded playbook currently says:

> "We only want the latest state."

and groups by `project_id` using `Table.Max` on `Snapshot_Date`. senior_power_bi_guide_full_data…

For a conventional campaign fact, that can make sense.

For WebRobots?

**Don't do it.**

It turns:

```text
Project A
Mar
Apr
May
Jun
Jul
Aug
```

into:

```text
Project A
Aug
```

You've just deleted the time series.

Instead:

```text
Fact_Campaign
        +
Fact_CampaignSnapshot
```

The first is your **one-row-per-project analytical master**, while the second is the **historical observation/event fact**.

---

# 10. WebRobots transformations

For each snapshot:

### Extract Snapshot Date

Suppose the file is named:

```text
Kickstarter_2023-05-18T03_20_08_715Z.csv
```

Create:

```text
SnapshotDate = 2023-05-18
```

using the filename.

### Convert Unix timestamps

WebRobots data commonly stores:

```text
deadline
state_changed_at
created_at
launched_at
```

as Unix timestamps. Published analysis converts exactly those fields into dates. [RStudio Pubs](https://rstudio-pubs-static.s3.amazonaws.com/337307_590d8c5747e94e398f01ba5f27fad781.html?utm_source=chatgpt.com)

In Power Query:

```powerquery
#datetime(1970,1,1,0,0,0)
    + #duration(0,0,0,[launched_at])
```

Then change to Date/Time.

### Parse nested JSON

You may see:

```text
category
location
profile
creator
urls
```

as JSON structures. Published analysis of this dataset confirms those fields are nested JSON. [RStudio Pubs](https://rstudio-pubs-static.s3.amazonaws.com/337307_590d8c5747e94e398f01ba5f27fad781.html?utm_source=chatgpt.com)

For category:

```text
Transform
→ Parse
→ JSON
→ Expand
```

Keep useful attributes such as:

```text
category.id
category.name
category.slug
category.parent_id
```

For location:

```text
location.name
location.displayable_name
location.country
location.state
```

Don't keep giant JSON blobs in the model.

---

# 11. Build `Dim_Project`

This should contain descriptive campaign information.

```text
Dim_Project
--------------------------------
ProjectKey
ProjectID
ProjectName
Slug
Blurb
ProjectURL
LaunchDate
DeadlineDate
CampaignDurationDays
```

Do **not** put:

```text
PledgedUSD
BackerCount
FundingRatio
```

here.

Those are facts/measures.

For `ProjectKey`, I'd use an integer surrogate key.

Example:

```text
ProjectKey
1
2
3
4
...
```

Power BI can use Power Query Index columns as surrogate keys. Microsoft specifically documents this approach for dimensions that need unique relationship keys. [Microsoft Learn](https://learn.microsoft.com/power-bi/guidance/star-schema?utm_source=chatgpt.com)

---

# 12. Build `Dim_Category`

Structure:

```text
CategoryKey
MainCategory
Subcategory
CategoryGroup
```

Example:

```text
CategoryKey | MainCategory | Subcategory
1           | Design       | Product Design
2           | Games        | Tabletop Games
3           | Music        | Rock
```

Create:

```text
Dim_Category
```

by taking distinct combinations of:

```text
MainCategory
Subcategory
```

Then:

```text
Add Column
→ Index Column
→ From 1
```

Now merge that key into the facts.

Your uploaded playbook also uses surrogate category IDs in this layer. senior_power_bi_guide_full_data…

---

# 13. Build `Dim_Location`

This should be more sophisticated than the previous:

```text
Country only
```

Create:

```text
Dim_Location
--------------------------------
LocationKey
CountryCode
CountryName
State
City
Latitude
Longitude
Region
```

Potential hierarchy:

```text
Country
 └── State
      └── City
```

Don't put:

```text
Total Pledged
Median Pledged
Mean Backers
City Population
```

into the dimension.

Those are metrics.

---

# 14. Build `Dim_Currency`

Very simple:

```text
CurrencyKey
CurrencyCode
CurrencySymbol
CurrencyName
```

For example:

```text
USD
GBP
EUR
CAD
AUD
```

This lets the model analyze native-currency campaigns separately.

---

# 15. Build `Dim_Status`

Create:

```text
StatusKey
Status
OutcomeGroup
IsCompleted
IsSuccessful
```

Example:

| Status | OutcomeGroup | IsCompleted | IsSuccessful |
| --- | --- | ---: | ---: |
| successful | Successful | 1 | 1 |
| failed | Failed | 1 | 0 |
| canceled | Canceled | 1 | 0 |
| suspended | Suspended | 1 | 0 |
| live | Active | 0 | 0 |

This is much better than hardcoding:

```DAX
state = "successful"
```

everywhere.

---

# 16. Build `Dim_Date`

Definitely use a proper date dimension.

Include:

```text
DateKey
Date
Year
Quarter
MonthNumber
MonthName
YearMonth
WeekNumber
DayOfWeek
DayName
IsWeekend
```

DAX:

```DAX
Dim_Date =
ADDCOLUMNS(
    CALENDAR(
        DATE(2009,1,1),
        DATE(2026,12,31)
    ),
    "DateKey", VALUE(FORMAT([Date], "yyyymmdd")),
    "Year", YEAR([Date]),
    "MonthNumber", MONTH([Date]),
    "MonthName", FORMAT([Date], "MMMM"),
    "YearMonth", FORMAT([Date], "YYYY-MM"),
    "Quarter", "Q" & FORMAT([Date], "Q"),
    "DayOfWeek", WEEKDAY([Date], 2),
    "DayName", FORMAT([Date], "dddd")
)
```

Then sort:

```text
MonthName → MonthNumber
```

and:

```text
YearMonth → Date
```

---

# 17. Fact 1 — `Fact_Campaign`

This is your main analytical fact.

Grain:

> **One row per unique Kickstarter project.**

Columns:

```text
ProjectKey
CategoryKey
LocationKey
CurrencyKey
StatusKey
LaunchDateKey
DeadlineDateKey

GoalLocal
GoalUSD
PledgedLocal
PledgedUSD
BackerCount

CampaignDurationDays
FundingRatio
PledgePerBacker
```

Don't include:

```text
ProjectName
Category
Country
City
CurrencyName
```

because those belong in dimensions.

---

# 18. Fact 2 — `Fact_CampaignSnapshot`

This is your WebRobots fact.

Grain:

> **One row per Project × SnapshotDate.**

Columns:

```text
ProjectKey
SnapshotDateKey
LaunchDateKey
DeadlineDateKey
StateChangedDateKey
CategoryKey
LocationKey
CurrencyKey
StatusKey

GoalLocal
PledgedLocal
PledgedUSD
ConvertedPledgedAmount
BackerCount
StaticUSDRate

StaffPickFlag
SpotlightFlag
IsStarrableFlag
```

This allows:

```text
Pledged growth over time
Backer growth over time
State transitions
Campaign activity by month
```

without contaminating the main fact.

---

# 19. Fact 3 — `Fact_CityMetrics`

Take MasterKickstarter geographic attributes and make a separate fact.

Possible grain:

```text
City × Period
```

Fields could be:

```text
LocationKey
DateKey
CityPopulation
TotalCityBackers
TotalCityPledged
MeanCampaignUSD
MedianCampaignUSD
MeanBackers
MedianBackers
```

The source analysis around this exact dataset demonstrates city-level metrics such as all-time backers and campaign pledge metrics. [GitHub](https://github.com/LeGriffon/Kickstarters_Data_Analysis?utm_source=chatgpt.com)

This means you can do things like:

> "Does a city's population correlate with Kickstarter activity?"

without multiplying city metrics across every individual campaign row.

---

# 20. Mapping.csv and County.csv

Your original guide calls these:

```text
Dim_State_Metrics
Dim_County_Metrics
```

I would **not automatically classify them as dimensions**.

The moment a table contains:

```text
TotalBackers
TotalUSD
MeanUSD
MedianUSD
ProjectCount
```

it is behaving much more like a **fact table**.

So I'd make:

```text
Fact_StateMetrics
Fact_CountyMetrics
```

with dimensions such as:

```text
Dim_Location
Dim_Date
```

around them.

That gives you a proper constellation.

---

# 21. Final relationship diagram

Your Power BI model should roughly become:

```text
                             Dim_Date
                              /  |  \
                             /   |   \
                            /    |    \
                           ▼     ▼     ▼

Dim_Category ────────────────► Fact_Campaign
                                  ▲
                                  │
Dim_Project ─────────────────────┤
                                  │
Dim_Location ────────────────────┤
                                  │
Dim_Currency ────────────────────┤
                                  │
Dim_Status ──────────────────────┘


                             Dim_Date
                                │
                                ▼
                    Fact_CampaignSnapshot
                       ▲       ▲       ▲
                       │       │       │
              Dim_Project   Dim_Category
                       │       │
                  Dim_Location
                       │
                  Dim_Currency
                       │
                   Dim_Status


                 Dim_Date
                    │
                    ▼
              Fact_CityMetrics
                    ▲
                    │
               Dim_Location


                 Dim_Date
                    │
                    ▼
             Fact_StateMetrics
                    ▲
                    │
               Dim_Location


                 Dim_Date
                    │
                    ▼
            Fact_CountyMetrics
                    ▲
                    │
               Dim_Location
```

No:

```text
Fact_Campaign ↔ Fact_CampaignSnapshot
```

direct relationship.

No many-to-many hack.

No bidirectional relationship unless there's a very specific reason.

Microsoft explicitly recommends using conformed dimensions between facts rather than directly relating fact tables many-to-many. [Microsoft Learn](https://learn.microsoft.com/en-us/power-bi/guidance/relationships-many-to-many?utm_source=chatgpt.com)

---

# 22. Relationship settings

Use:

```text
Cardinality: One-to-many
Cross-filter direction: Single
```

For example:

```text
Dim_Category[CategoryKey]
        1
        │
        ▼
Fact_Campaign[CategoryKey]
        *
```

and:

```text
Dim_Project[ProjectKey]
        1
        │
        ▼
Fact_CampaignSnapshot[ProjectKey]
        *
```

The dimension is always the `1`.

The fact is always the `*`.

That's the clean Power BI pattern. [Microsoft Learn](https://learn.microsoft.com/power-bi/guidance/star-schema?utm_source=chatgpt.com)

---

# 23. Date relationships

You have multiple date roles:

```text
Launch
Deadline
State Changed
Created
Snapshot
```

Don't create random relationships between all of them.

For the core campaign fact:

```text
Dim_Date[DateKey]
       1
       │
       ▼
Fact_Campaign[LaunchDateKey]
       *
```

For deadline, you have two choices.

### Option A — inactive relationship

```text
Dim_Date[DateKey]
       1
       │
       ▼
Fact_Campaign[DeadlineDateKey]
```

inactive.

Then:

```DAX
Projects by Deadline =
CALCULATE(
    [Total Projects],
    USERELATIONSHIP(
        Dim_Date[DateKey],
        Fact_Campaign[DeadlineDateKey]
    )
)
```

### Option B — role-playing date dimensions

For a polished enterprise-style project, you can have:

```text
Dim_LaunchDate
Dim_DeadlineDate
Dim_SnapshotDate
Dim_StateChangedDate
```

This is more tables but can make the semantic model much easier to use. Microsoft discusses role-playing date dimensions as a valid design technique. [Microsoft Learn](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema?WT.mc_id=AI-MVP-5004077\&utm_source=chatgpt.com)

For **your project**, I'd use separate role-playing date dimensions for the most important dates because your dashboard is fundamentally temporal.

---

# 24. Your main DAX measures

Create a dedicated:

```text
Measures
```

table.

## Core

```DAX
Total Projects =
DISTINCTCOUNT(Fact_Campaign[ProjectKey])
```

```DAX
Successful Projects =
CALCULATE(
    [Total Projects],
    Dim_Status[Status] = "successful"
)
```

```DAX
Failed Projects =
CALCULATE(
    [Total Projects],
    Dim_Status[Status] = "failed"
)
```

```DAX
Total Pledged USD =
SUM(Fact_Campaign[PledgedUSD])
```

```DAX
Total Goal USD =
SUM(Fact_Campaign[GoalUSD])
```

```DAX
Total Backers =
SUM(Fact_Campaign[BackerCount])
```

```DAX
Success Rate =
DIVIDE(
    [Successful Projects],
    [Total Projects],
    0
)
```

---

# 25. Funding measures

```DAX
Funding Ratio =
DIVIDE(
    [Total Pledged USD],
    [Total Goal USD],
    0
)
```

```DAX
Average Pledged per Backer =
DIVIDE(
    [Total Pledged USD],
    [Total Backers],
    0
)
```

```DAX
Average Goal per Project =
DIVIDE(
    [Total Goal USD],
    [Total Projects],
    0
)
```

```DAX
Average Pledged per Project =
DIVIDE(
    [Total Pledged USD],
    [Total Projects],
    0
)
```

---

# 26. Snapshot measures

This is where the model becomes much more interesting.

```DAX
Snapshot Pledged USD =
SUM(Fact_CampaignSnapshot[PledgedUSD])
```

```DAX
Snapshot Backers =
SUM(Fact_CampaignSnapshot[BackerCount])
```

```DAX
Previous Snapshot Pledged =
CALCULATE(
    [Snapshot Pledged USD],
    DATEADD(
        Dim_Date[Date],
        -1,
        MONTH
    )
)
```

```DAX
Pledged Growth =
[Snapshot Pledged USD] - [Previous Snapshot Pledged]
```

```DAX
Pledged Growth % =
DIVIDE(
    [Pledged Growth],
    [Previous Snapshot Pledged],
    0
)
```

Then you can create a real:

```text
Kickstarter funding trajectory
```

dashboard.

---

# 27. Success-rate calculation: be careful

Don't simply use:

```DAX
Successful / All
```

without considering `live`.

Your status table gives you the flexibility to distinguish:

```text
Completed campaigns
Active campaigns
Successful campaigns
Failed campaigns
Canceled campaigns
Suspended campaigns
```

For example:

```DAX
Completed Projects =
CALCULATE(
    [Total Projects],
    Dim_Status[IsCompleted] = 1
)
```

```DAX
Completed Success Rate =
DIVIDE(
    [Successful Projects],
    [Completed Projects],
    0
)
```

That's much more defensible analytically.

---

# 28. Power Query transformation order

Don't randomly transform columns.

Use this order:

```text
SOURCE
 ↓
Promote Headers
 ↓
Remove Blank/Unnamed Columns
 ↓
Standardize Column Names
 ↓
Clean Text
 ↓
Parse JSON
 ↓
Convert Dates
 ↓
Convert Numeric Types
 ↓
Normalize Categories
 ↓
Normalize Geography
 ↓
Add Source Metadata
 ↓
Add Snapshot Date
 ↓
Add Derived Columns
 ↓
Remove Unused Columns
 ↓
Deduplicate only at the correct grain
 ↓
Merge Dimension Keys
 ↓
Final Fact
```

This makes debugging dramatically easier.

Power Query supports Reference queries and Merge operations specifically for this layered approach; Microsoft describes a reference query as reusing the prior query's result chain rather than creating an unrelated copy. [Microsoft Learn](https://learn.microsoft.com/en-us/power-bi/guidance/power-query-referenced-queries?utm_source=chatgpt.com)

---

# 29. Add source lineage

Every important staging/conformed row should retain:

```text
SourceSystem
SourceFile
SourceSnapshotDate
```

For example:

```text
Kaggle_2016
Kaggle_2018
MasterKickstarter
WebRobots
```

This will save you later when someone asks:

> "Why is this project's pledge amount different from that table?"

You can trace it back immediately.

---

# 30. The most important deduplication rule

For:

### `Fact_Campaign`

deduplicate by:

```text
ProjectID
```

after resolving source priority.

For example:

```text
MasterKickstarter
    priority 1

Kaggle 2018
    priority 2

Kaggle 2016
    priority 3
```

But for:

### `Fact_CampaignSnapshot`

deduplicate by:

```text
ProjectID + SnapshotDate
```

not:

```text
ProjectID
```

So:

```text
ProjectID | SnapshotDate
-----------+-------------
1001      | 2023-01-05
1001      | 2023-02-16
1001      | 2023-03-09
```

are **three legitimate observations**, not duplicates.

---

# 31. Source priority

I'd make a `SourcePriority` column:

```text
MasterKickstarter = 1
Kaggle_2018        = 2
Kaggle_2016        = 3
WebRobots          = 4
```

But don't blindly say "Master always wins".

Instead, define priority **per attribute** where necessary.

For example:

```text
Campaign metadata → Master
Historical outcome → Kaggle
Current/latest observation → WebRobots
Snapshot metrics → WebRobots
Geographic enrichment → Master
```

This is much more mature than saying:

> "latest source wins."

---

# 32. QA queries you absolutely should build

Your earlier playbook already includes duplicate and missing-key checks. senior_power_bi_guide_full_data…

Expand them.

### QA 1 — Duplicate projects

```text
ProjectID
Count Rows
```

Filter:

```text
> 1
```

for `Fact_Campaign`.

Should be zero.

---

### QA 2 — Duplicate snapshots

Group:

```text
ProjectID
SnapshotDate
```

Filter:

```text
Count > 1
```

Should be zero.

---

### QA 3 — Missing CategoryKey

Filter:

```text
CategoryKey = null
```

Should be zero.

---

### QA 4 — Missing LocationKey

```text
LocationKey = null
```

Investigate.

---

### QA 5 — Impossible duration

```text
DurationDays < 0
```

---

### QA 6 — Impossible funding

```text
GoalUSD < 0
PledgedUSD < 0
BackerCount < 0
```

---

### QA 7 — Success logic

Find:

```text
ProjectStatus = successful
FundingRatio < 1
```

Don't automatically call them errors because Kickstarter status and amount semantics can have edge cases. Investigate instead.

---

### QA 8 — Orphan keys

Every fact FK should exist in its dimension:

```text
Fact → Dim_Project
Fact → Dim_Category
Fact → Dim_Location
Fact → Dim_Currency
Fact → Dim_Status
```

---

# 33. The Power BI model should have no raw columns visible

Hide:

```text
ProjectKey
CategoryKey
LocationKey
CurrencyKey
StatusKey
DateKey
```

from report view.

Microsoft's modeling guidance also supports hiding relationship keys from report authors. [Microsoft Learn](https://learn.microsoft.com/en-us/power-bi/guidance/relationships-many-to-many?utm_source=chatgpt.com)

The report creator should see:

```text
Project Name
Category
Country
City
Status
Launch Year
Pledged USD
Backers
Success Rate
```

—not a sea of technical IDs.

---

# 34. What I would NOT do

Don't build:

```text
MasterKickstarter
       ↓
Merged Kaggle 2016
       ↓
Merged Kaggle 2018
       ↓
Merged WebRobots
       ↓
one giant table
```

That creates:

```text
duplicate projects
duplicated metrics
mixed grains
ambiguous dates
inflated totals
broken relationships
```

Also don't do:

```text
Fact_Campaign ↔ Fact_CampaignSnapshot
```

with a many-to-many relationship.

And don't make:

```text
Mapping
County
```

dimensions just because they contain geography names if they actually contain measurements.

---

# 35. What the final model gives you

Once built, you can answer **three different analytical classes**.

### Campaign performance

```text
Which categories succeed?
Which countries raise the most?
Which campaigns have the highest funding ratios?
What is average pledge per backer?
```

### Geographic intelligence

```text
Which states generate the most projects?
Which cities generate the most backing?
Does population correlate with Kickstarter activity?
Which regions have the best success rates?
```

### Temporal/snapshot intelligence

```text
How does pledged funding change across snapshots?
How quickly do projects gain backers?
Which campaigns were accelerating?
How does campaign status change over time?
```

That last category is something you simply cannot do correctly after collapsing WebRobots to one "latest record".

---

# 36. Recommended Power BI report pages

I'd build the report around the galaxy model rather than around individual source datasets.

### Page 1 — Executive Overview

Cards:

```text
Total Projects
Successful Projects
Success Rate
Total Pledged
Total Backers
Average Pledged / Backer
```

Visuals:

```text
Projects by Year
Pledged USD by Year
Success Rate by Category
Top Countries
```

---

### Page 2 — Campaign Performance

```text
Goal vs Pledged
Funding Ratio distribution
Success rate by category/subcategory
Backers by category
Campaign duration vs success
```

---

### Page 3 — Geographic Intelligence

```text
Map
Projects by country
Projects by state
Pledged by state
Backers by city
City population vs project activity
```

This is where your MasterKickstarter geographic data becomes useful.

---

### Page 4 — Campaign Lifecycle

Use:

```text
Fact_CampaignSnapshot
```

Visuals:

```text
Pledged over snapshot month
Backers over snapshot month
Status changes
Top accelerating campaigns
Pledged growth %
```

---

### Page 5 — Project Explorer

A detailed table:

```text
Project
Category
Country
City
Launch Date
Deadline
Status
Goal
Pledged
Backers
Funding %
```

with drillthrough into a project.

---

### Page 6 — Data Quality

Hide this from normal users or make it developer-only.

Show:

```text
Duplicate rows
Missing keys
Unknown categories
Unknown locations
Invalid dates
Invalid monetary values
Snapshot anomalies
```

That makes the project feel like an actual BI engineering project rather than just a dashboard.

---

# 37. One more improvement: don't treat every source as equally authoritative

I would document this matrix:

| Business Attribute | Preferred Source |
| --- | --- |
| Project identity | Master / Kaggle |
| Original campaign goal | Kaggle |
| Original pledge | Kaggle |
| Original outcome | Kaggle / Master |
| Geographic enrichment | Master |
| Monthly observed pledge | WebRobots |
| Monthly backers | WebRobots |
| Snapshot status | WebRobots |
| Campaign JSON metadata | WebRobots |
| Source lineage | All |

That gives you a defensible **data contract**.

---

# 38. Your final Power Query dependency chain

The clean dependency graph should look like:

```text
                 RAW FILES
                    │
        ┌───────────┼────────────┐
        ▼           ▼            ▼
     Kaggle       Master      WebRobots
        │           │            │
        ▼           ▼            ▼
     Staging      Staging      Staging
        │           │            │
        └───────────┼────────────┘
                    ▼
              CONFORMED LAYER
                    │
        ┌───────────┼───────────────┐
        ▼           ▼               ▼
   Dimensions    Campaign Fact   Snapshot Fact
        │                           │
        └────────────┬──────────────┘
                     ▼
                 QA LAYER
                     │
                     ▼
              POWER BI MODEL
                     │
                     ▼
                  DAX
                     │
                     ▼
                 REPORTS
```

This is much closer to an actual analytics-engineering workflow.

And there is a reason I'm pushing the layered approach: Power BI's own documentation recommends using Power Query for source preparation and dimensional modeling for the semantic model, while also warning that query references don't magically cache upstream results—so the design should be intentional rather than creating dozens of expensive references to the same massive source. [Microsoft Learn](https://learn.microsoft.com/power-bi/guidance/star-schema?utm_source=chatgpt.com)

---

## The implementation order I'd use in Power BI

Do it in this exact order:

**1. Download and freeze the source files.**  
**2. Create the `00–99` query groups.**  
**3. Build the three source ingestion queries.**  
**4. Build the Kaggle staging queries.**  
**5. Build the Master staging query.**  
**6. Build the WebRobots staging/snapshot query.**  
**7. Build the conformed project/category/location/status tables.**  
**8. Build the dimensions.**  
**9. Build `Fact_Campaign`.**  
**10. Build `Fact_CampaignSnapshot`.**  
**11. Build geographic facts.**  
**12. Create `Dim_Date`.**  
**13. Create relationships.**  
**14. Add DAX measures.**  
**15. Run QA.**  
**16. Only then start the dashboard UI.**

The key architectural difference from your uploaded guide is:

```text
OLD:
All sources
   ↓
One deduplicated Project Universe
   ↓
One Fact

NEW:
Kaggle + Master
      ↓
Fact_Campaign

WebRobots monthly snapshots
      ↓
Fact_CampaignSnapshot

Master geographic aggregates
      ↓
Fact_CityMetrics / Fact_StateMetrics / Fact_CountyMetrics

All of them
      ↓
Conformed Dimensions
```

That is the architecture I'd use for a serious portfolio-level Power BI project.

### Sources

The WebRobots source currently lists monthly Kickstarter crawls from March 2016 onward, including 2026 snapshots. [Web Scraping Service](https://webrobots.io/kickstarter-datasets/)  
The Kaggle dataset structure is documented as 15 campaign fields including dates, goal, pledges, state, backers, country and USD conversions. [GitHub](https://github.com/ayoubabozer/kickstarter?utm_source=chatgpt.com)  
A project using the exact `wood2174/mapkickstarter` dataset describes `MasterKickstarter.csv` as ~99,000 projects with 57 attributes, while published analysis shows its geographic/campaign enrichment fields. [GitHub](https://github.com/LeGriffon/Kickstarters_Data_Analysis?utm_source=chatgpt.com)  
Microsoft's current Power BI guidance supports the dimension/fact approach, one-to-many relationships, surrogate keys, and using conformed dimensions rather than direct fact-to-fact many-to-many relationships. [Microsoft Learn](https://learn.microsoft.com/power-bi/guidance/star-schema?utm_source=chatgpt.com)
