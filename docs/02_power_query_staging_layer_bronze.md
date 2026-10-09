# 02 — Power Query Staging Layer (Bronze) Guide

## Building the Clean Staging Layer (Bronze)

The **Staging Layer** represents the first transformation step in our Medallion architecture. Staging queries take raw files from `01_Sources` and apply strict data hygiene:
1. Correcting encoding errors and removing phantom columns.
2. Trimming invisible whitespace and standardizing string casing.
3. Casting strict data types (Currency, Int64, DateTime, Date, Text).
4. Converting UNIX epoch integer timestamps to proper DateTime objects.
5. Calculating base duration days and funding ratios.
6. Attaching source lineage metadata (`Source_System`, `Snapshot_Date`).

> [!IMPORTANT]
> **Enable Load Rule**: Every query in `02_Staging` must have **Enable Load = False**. Staging queries are internal pipeline dependencies and should never be loaded directly into the reporting data model.

---

## 1. Staging Query 1: `Stg_Kaggle_2016`

### Objective
- Eliminate the 4 phantom columns (`Unnamed: 13` through `16`) caused by unescaped commas in text fields.
- Strip trailing spaces from column names (e.g., `'ID '` → `'ProjectID'`).
- Handle the absence of non-USD goal conversions by setting `GoalUSD` conditionally and flagging `HasGoalUSD`.

### Complete Power Query M Script
```powerquery
let
    // 1. Reference the raw source
    Source = Src_Kaggle_2016,

    // 2. Select only the 13 legitimate columns, dropping phantom spillover columns
    #"Choose Columns" = Table.SelectColumns(
        Source,
        {
            "ID ", "name ", "category ", "main_category ", "currency ",
            "deadline ", "goal ", "launched ", "pledged ", "state ",
            "backers ", "country ", "usd pledged "
        }
    ),

    // 3. Rename to canonical enterprise column names
    #"Renamed Columns" = Table.RenameColumns(
        #"Choose Columns",
        {
            {"ID ", "ProjectID"},
            {"name ", "ProjectName"},
            {"category ", "Subcategory"},
            {"main_category ", "Category"},
            {"currency ", "CurrencyCode"},
            {"deadline ", "DeadlineDateTime"},
            {"goal ", "GoalLocal"},
            {"launched ", "LaunchDateTime"},
            {"pledged ", "PledgedLocal"},
            {"state ", "ProjectStatus"},
            {"backers ", "BackerCount"},
            {"country ", "CountryCode"},
            {"usd pledged ", "PledgedUSD"}
        }
    ),

    // 4. Clean and Trim text attributes
    #"Trimmed Text" = Table.TransformColumns(
        #"Renamed Columns",
        {
            {"ProjectName", each Text.Trim(_), type nullable text},
            {"Subcategory", each Text.Trim(_), type nullable text},
            {"Category", each Text.Trim(_), type nullable text},
            {"CurrencyCode", each Text.Trim(_), type nullable text},
            {"ProjectStatus", each Text.Trim(_), type nullable text},
            {"CountryCode", each Text.Trim(_), type nullable text}
        }
    ),
    #"Cleaned Text" = Table.TransformColumns(
        #"Trimmed Text",
        {
            {"ProjectName", each Text.Clean(_), type nullable text},
            {"Subcategory", each Text.Clean(_), type nullable text},
            {"Category", each Text.Clean(_), type nullable text},
            {"CurrencyCode", each Text.Clean(_), type nullable text},
            {"ProjectStatus", each Text.Clean(_), type nullable text},
            {"CountryCode", each Text.Clean(_), type nullable text}
        }
    ),
    #"Proper Cased Status" = Table.TransformColumns(
        #"Cleaned Text",
        {{"ProjectStatus", each Text.Proper(_), type nullable text}}
    ),

    // 5. Handle Goal USD (Kaggle 2016 only has usd pledged; USD currency has 1:1 goal)
    #"Added GoalUSD" = Table.AddColumn(
        #"Proper Cased Status",
        "GoalUSD",
        each if [CurrencyCode] = null or [GoalLocal] = null then null
             else if Text.Upper(Text.Trim([CurrencyCode])) = "USD" then [GoalLocal]
             else null,
        Currency.Type
    ),
    #"Added HasGoalUSD" = Table.AddColumn(
        #"Added GoalUSD",
        "HasGoalUSD",
        each if [GoalUSD] = null then false else true,
        type logical
    ),

    // 6. Explicit Currency and Number Casting
    #"Changed Numeric Types" = Table.TransformColumnTypes(
        #"Added HasGoalUSD",
        {
            {"PledgedUSD", Currency.Type},
            {"GoalLocal", Currency.Type},
            {"PledgedLocal", Currency.Type},
            {"BackerCount", Int64.Type},
            {"ProjectID", Int64.Type}
        }
    ),

    // 7. Temporal Decomposition
    #"Inserted LaunchDate" = Table.AddColumn(
        #"Changed Numeric Types",
        "LaunchDate",
        each DateTime.Date([LaunchDateTime]),
        type nullable date
    ),
    #"Inserted LaunchYear" = Table.AddColumn(
        #"Inserted LaunchDate",
        "LaunchYear",
        each Date.Year([LaunchDateTime]),
        Int64.Type
    ),
    #"Inserted LaunchMonth" = Table.AddColumn(
        #"Inserted LaunchYear",
        "LaunchMonth",
        each Date.Month([LaunchDateTime]),
        Int64.Type
    ),
    #"Inserted LaunchQuarter" = Table.AddColumn(
        #"Inserted LaunchMonth",
        "LaunchQuarter",
        each "Q" & Text.From(Date.QuarterOfYear([LaunchDateTime])),
        type text
    ),
    #"Inserted DeadlineDate" = Table.AddColumn(
        #"Inserted LaunchQuarter",
        "DeadlineDate",
        each DateTime.Date([DeadlineDateTime]),
        type nullable date
    ),

    // 8. Derived Campaign Durations and Performance Ratios
    #"Added CampaignDurationDays" = Table.AddColumn(
        #"Inserted DeadlineDate",
        "CampaignDurationDays",
        each if [LaunchDate] = null or [DeadlineDate] = null then null
             else Duration.Days([DeadlineDate] - [LaunchDate]),
        Int64.Type
    ),
    #"Added GoalAchievementPct" = Table.AddColumn(
        #"Added CampaignDurationDays",
        "GoalAchievementPct",
        each if [GoalUSD] = null or [GoalUSD] = 0 or [PledgedUSD] = null then null
             else [PledgedUSD] / [GoalUSD],
        Percentage.Type
    ),
    #"Added PledgePerBacker" = Table.AddColumn(
        #"Added GoalAchievementPct",
        "PledgePerBacker",
        each if [PledgedUSD] = null or [BackerCount] = null or [BackerCount] = 0 then null
             else [PledgedUSD] / [BackerCount],
        Currency.Type
    ),

    // 9. Source Lineage & Recency Metadata
    #"Added Source System" = Table.AddColumn(
        #"Added PledgePerBacker",
        "Source_System",
        each "Kaggle_2016",
        type text
    ),
    #"Added Snapshot Date" = Table.AddColumn(
        #"Added Source System",
        "Snapshot_Date",
        each #date(2016, 12, 31),
        type date
    ),

    // 10. Reorder to Canonical Order
    #"Reordered Columns" = Table.ReorderColumns(
        #"Added Snapshot Date",
        {
            "ProjectID", "ProjectName", "Subcategory", "Category", "CurrencyCode",
            "CountryCode", "GoalLocal", "PledgedLocal", "GoalUSD", "PledgedUSD",
            "BackerCount", "ProjectStatus", "LaunchDateTime", "LaunchDate", "LaunchYear",
            "LaunchMonth", "LaunchQuarter", "DeadlineDateTime", "DeadlineDate",
            "CampaignDurationDays", "GoalAchievementPct", "PledgePerBacker", "HasGoalUSD",
            "Source_System", "Snapshot_Date"
        }
    )
in
    #"Reordered Columns"
```

---

## 2. Staging Query 2: `Stg_Kaggle_2018`

### Objective
- Standardize Kaggle 2018 into the canonical schema.
- Map Fixer.io conversions (`usd_pledged_real` → `PledgedUSD`, `usd_goal_real` → `GoalUSD`).
- Preserve original Kickstarter USD conversion as `PledgedUSD_KS` for auditability.

### Complete Power Query M Script
```powerquery
let
    // 1. Reference the raw source
    Source = Src_Kaggle_2018,

    // 2. Canonical Column Renaming
    #"Renamed Columns" = Table.RenameColumns(
        Source,
        {
            {"ID", "ProjectID"},
            {"name", "ProjectName"},
            {"category", "Subcategory"},
            {"main_category", "Category"},
            {"currency", "CurrencyCode"},
            {"deadline", "DeadlineDate"},
            {"goal", "GoalLocal"},
            {"launched", "LaunchDateTime"},
            {"pledged", "PledgedLocal"},
            {"state", "ProjectStatus"},
            {"backers", "BackerCount"},
            {"country", "CountryCode"},
            {"usd pledged", "PledgedUSD_KS"},
            {"usd_pledged_real", "PledgedUSD"},
            {"usd_goal_real", "GoalUSD"}
        }
    ),

    // 3. Text Sanitization
    #"Trimmed Text" = Table.TransformColumns(
        #"Renamed Columns",
        {
            {"ProjectName", each Text.Trim(_), type nullable text},
            {"Subcategory", each Text.Trim(_), type nullable text},
            {"Category", each Text.Trim(_), type nullable text},
            {"CurrencyCode", each Text.Trim(_), type nullable text},
            {"CountryCode", each Text.Trim(_), type nullable text},
            {"ProjectStatus", each Text.Trim(_), type nullable text}
        }
    ),
    #"Cleaned Text" = Table.TransformColumns(
        #"Trimmed Text",
        {
            {"ProjectName", each Text.Clean(_), type nullable text},
            {"Subcategory", each Text.Clean(_), type nullable text},
            {"Category", each Text.Clean(_), type nullable text},
            {"CurrencyCode", each Text.Clean(_), type nullable text},
            {"CountryCode", each Text.Clean(_), type nullable text},
            {"ProjectStatus", each Text.Clean(_), type nullable text}
        }
    ),
    #"Proper Cased Status" = Table.TransformColumns(
        #"Cleaned Text",
        {{"ProjectStatus", each Text.Proper(_), type nullable text}}
    ),

    // 4. Temporal Columns
    #"Inserted LaunchDate" = Table.AddColumn(
        #"Proper Cased Status",
        "LaunchDate",
        each DateTime.Date([LaunchDateTime]),
        type nullable date
    ),
    #"Inserted LaunchYear" = Table.AddColumn(
        #"Inserted LaunchDate",
        "LaunchYear",
        each Date.Year([LaunchDateTime]),
        Int64.Type
    ),
    #"Inserted LaunchMonth" = Table.AddColumn(
        #"Inserted LaunchYear",
        "LaunchMonth",
        each Date.Month([LaunchDate]),
        Int64.Type
    ),
    #"Inserted LaunchQuarter" = Table.AddColumn(
        #"Inserted LaunchMonth",
        "LaunchQuarter",
        each "Q" & Text.From(Date.QuarterOfYear([LaunchDate])),
        type text
    ),
    #"Calculated Duration" = Table.AddColumn(
        #"Inserted LaunchQuarter",
        "CampaignDurationDays",
        each Duration.Days([DeadlineDate] - [LaunchDate]),
        Int64.Type
    ),

    // 5. Type Conversions
    #"Changed Types" = Table.TransformColumnTypes(
        #"Calculated Duration",
        {
            {"ProjectID", Int64.Type},
            {"GoalLocal", Currency.Type},
            {"PledgedLocal", Currency.Type},
            {"GoalUSD", Currency.Type},
            {"PledgedUSD", Currency.Type},
            {"PledgedUSD_KS", Currency.Type},
            {"BackerCount", Int64.Type}
        }
    ),

    // 6. Metrics & Lineage
    #"Added GoalAchievementPct" = Table.AddColumn(
        #"Changed Types",
        "GoalAchievementPct",
        each if [GoalUSD] = null or [GoalUSD] = 0 or [PledgedUSD] = null then null
             else [PledgedUSD] / [GoalUSD],
        Percentage.Type
    ),
    #"Added PledgePerBacker" = Table.AddColumn(
        #"Added GoalAchievementPct",
        "PledgePerBacker",
        each if [BackerCount] = null or [BackerCount] = 0 or [PledgedUSD] = null then null
             else [PledgedUSD] / [BackerCount],
        Currency.Type
    ),
    #"Added HasGoalUSD" = Table.AddColumn(
        #"Added PledgePerBacker",
        "HasGoalUSD",
        each true,
        type logical
    ),
    #"Added Source System" = Table.AddColumn(
        #"Added HasGoalUSD",
        "Source_System",
        each "Kaggle_2018",
        type text
    ),
    #"Added Snapshot Date" = Table.AddColumn(
        #"Added Source System",
        "Snapshot_Date",
        each #date(2018, 1, 1),
        type date
    ),

    // 7. Canonical Order
    #"Reordered Columns" = Table.ReorderColumns(
        #"Added Snapshot Date",
        {
            "ProjectID", "ProjectName", "Subcategory", "Category", "CurrencyCode",
            "CountryCode", "GoalLocal", "PledgedLocal", "GoalUSD", "PledgedUSD",
            "PledgedUSD_KS", "BackerCount", "ProjectStatus", "LaunchDateTime", "LaunchDate",
            "LaunchYear", "LaunchMonth", "LaunchQuarter", "DeadlineDate", "CampaignDurationDays",
            "GoalAchievementPct", "PledgePerBacker", "HasGoalUSD", "Source_System", "Snapshot_Date"
        }
    )
in
    #"Reordered Columns"
```

---

## 3. Staging Query 3: `Stg_MasterKickstarter`

### Objective
- Parse 57 attributes using modular M cleaning functions.
- Safely parse UNIX integer epoch timestamps into DateTime objects.
- Separate campaign entity attributes from city demographic aggregates.

### Complete Power Query M Script
```powerquery
let
    Source = Src_MasterKickstarter,

    // Reusable parsing functions
    CleanText = (val as any) as nullable text =>
        if val = null then null
        else
            let t = Text.Clean(Text.Trim(Text.From(val))) in
            if t = "" or t = "NA" or t = "null" or t = "N/A" then null else t,

    CleanNumber = (val as any) as nullable number =>
        if val = null then null
        else
            let t = CleanText(val) in
            if t = null then null
            else
                try Number.FromText(Text.Select(t, {"0".."9", "-", ".", "E", "e"}))
                otherwise null,

    CleanDateTime = (val as any) as nullable datetime =>
        if val = null then null
        else
            let t = CleanText(val) in
            if t = null then null
            else
                try DateTime.FromText(t)
                otherwise
                    try #datetime(1970, 1, 1, 0, 0, 0) + #duration(0, 0, 0, Number.FromText(t))
                    otherwise null,

    // Rename identifiers & financials
    #"Renamed Canonical Columns" = Table.RenameColumns(
        Source,
        {
            {"id", "ProjectID"},
            {"name", "ProjectName"},
            {"blurb", "Blurb"},
            {"slug", "ProjectSlug"},
            {"Categories", "Category"},
            {"status", "ProjectStatus"},
            {"currency", "CurrencyCode"},
            {"currency_symbol", "CurrencySymbol"},
            {"currency_trailing_code", "CurrencyTrailingCode"},
            {"Country", "CountryName"},
            {"goal", "GoalLocal"},
            {"pledged", "PledgedLocal"},
            {"pledgedUSD", "PledgedUSD"},
            {"backers_count", "BackerCount"},
            {"staff_pick", "StaffPickFlag"},
            {"spotLight", "SpotlightFlag"},
            {"disable_communication", "DisableCommunicationFlag"},
            {"created_at", "CreatedDateTime"},
            {"launched_at", "LaunchDateTime"},
            {"deadline", "DeadlineDateTime"},
            {"state_changed_at", "StateChangedDateTime"}
        },
        MissingField.Ignore
    ),

    // Transform Category & Status
    #"Normalized Category" = Table.ReplaceValue(
        #"Renamed Canonical Columns",
        "Film Video", "Film & Video",
        Replacer.ReplaceValue, {"Category"}
    ),
    #"Added Subcategory" = Table.AddColumn(
        #"Normalized Category",
        "Subcategory",
        each "General",
        type text
    ),

    // Clean Numbers & Types
    #"Cleaned Numeric" = Table.TransformColumns(
        #"Added Subcategory",
        {
            {"ProjectID", each CleanNumber(_), Int64.Type},
            {"GoalLocal", each CleanNumber(_), Currency.Type},
            {"PledgedLocal", each CleanNumber(_), Currency.Type},
            {"PledgedUSD", each CleanNumber(_), Currency.Type},
            {"BackerCount", each CleanNumber(_), Int64.Type},
            {"Latitude", each CleanNumber(_), type nullable number},
            {"Longitude", each CleanNumber(_), type nullable number},
            {"City_Pop", each CleanNumber(_), Int64.Type}
        },
        null, MissingField.Ignore
    ),

    // Clean Dates
    #"Cleaned Dates" = Table.TransformColumns(
        #"Cleaned Numeric",
        {
            {"CreatedDateTime", each CleanDateTime(_), type nullable datetime},
            {"LaunchDateTime", each CleanDateTime(_), type nullable datetime},
            {"DeadlineDateTime", each CleanDateTime(_), type nullable datetime},
            {"StateChangedDateTime", each CleanDateTime(_), type nullable datetime}
        },
        null, MissingField.Ignore
    ),

    // Extract Dates
    #"Inserted LaunchDate" = Table.AddColumn(
        #"Cleaned Dates", "LaunchDate",
        each if [LaunchDateTime] <> null then DateTime.Date([LaunchDateTime]) else null,
        type nullable date
    ),
    #"Inserted DeadlineDate" = Table.AddColumn(
        #"Inserted LaunchDate", "DeadlineDate",
        each if [DeadlineDateTime] <> null then DateTime.Date([DeadlineDateTime]) else null,
        type nullable date
    ),

    // Durations
    #"Added CampaignDurationDays" = Table.AddColumn(
        #"Inserted DeadlineDate", "CampaignDurationDays",
        each if [LaunchDate] = null or [DeadlineDate] = null then null
             else Duration.Days([DeadlineDate] - [LaunchDate]),
        Int64.Type
    ),
    #"Added GoalUSD" = Table.AddColumn(
        #"Added CampaignDurationDays", "GoalUSD",
        each if [CurrencyCode] = "USD" then [GoalLocal] else null,
        Currency.Type
    ),
    #"Added GoalAchievementPct" = Table.AddColumn(
        #"Added GoalUSD", "GoalAchievementPct",
        each if [GoalUSD] = null or [GoalUSD] = 0 or [PledgedUSD] = null then null
             else [PledgedUSD] / [GoalUSD],
        Percentage.Type
    ),
    #"Added PledgePerBacker" = Table.AddColumn(
        #"Added GoalAchievementPct", "PledgePerBacker",
        each if [BackerCount] = null or [BackerCount] = 0 or [PledgedUSD] = null then null
             else [PledgedUSD] / [BackerCount],
        Currency.Type
    ),

    // Metadata
    #"Added Source Lineage" = Table.AddColumn(
        #"Added PledgePerBacker", "Source_System",
        each "MasterKickstarter", type text
    ),
    #"Added Snapshot Date" = Table.AddColumn(
        #"Added Source Lineage", "Snapshot_Date",
        each #date(2017, 12, 31), type date
    )
in
    #"Added Snapshot Date"
```

---

## 4. Staging Query 4: `Stg_WebRobots`

### Objective
- Standardize the consolidated WebRobots enrichment dataset.
- Provide canonical columns matching `Stg_Kaggle_2018`.

```powerquery
let
    Source = Src_WebRobots_Latest,
    #"Renamed Columns" = Table.RenameColumns(
        Source,
        {
            {"project_id", "ProjectID"},
            {"name", "ProjectName"},
            {"state", "ProjectStatus"},
            {"category_name", "Category"},
            {"subcategory_name", "Subcategory"},
            {"country", "CountryCode"},
            {"launched_at", "LaunchDateTime"},
            {"deadline_at", "DeadlineDateTime"},
            {"goal_usd", "GoalUSD"},
            {"pledged_usd", "PledgedUSD"},
            {"backers_count", "BackerCount"}
        }
    ),
    #"Proper Cased Status" = Table.TransformColumns(
        #"Renamed Columns",
        {{"ProjectStatus", each Text.Proper(_), type nullable text}}
    ),
    #"Inserted LaunchDate" = Table.AddColumn(
        #"Proper Cased Status", "LaunchDate",
        each DateTime.Date([LaunchDateTime]), type nullable date
    ),
    #"Inserted DeadlineDate" = Table.AddColumn(
        #"Inserted LaunchDate", "DeadlineDate",
        each DateTime.Date([DeadlineDateTime]), type nullable date
    ),
    #"Calculated Duration" = Table.AddColumn(
        #"Inserted DeadlineDate", "CampaignDurationDays",
        each Duration.Days([DeadlineDate] - [LaunchDate]), Int64.Type
    ),
    #"Added GoalAchievementPct" = Table.AddColumn(
        #"Calculated Duration", "GoalAchievementPct",
        each if [GoalUSD] = null or [GoalUSD] = 0 or [PledgedUSD] = null then null
             else [PledgedUSD] / [GoalUSD], Percentage.Type
    ),
    #"Added CurrencyCode" = Table.AddColumn(
        #"Added GoalAchievementPct", "CurrencyCode",
        each "USD", type text
    ),
    #"Added Source Metadata" = Table.AddColumn(
        #"Added CurrencyCode", "Source_System",
        each "WebRobots", type text
    ),
    #"Added Snapshot Date" = Table.AddColumn(
        #"Added Source Metadata", "Snapshot_Date",
        each #date(2026, 9, 10), type date
    )
in
    #"Added Snapshot Date"
```

---

## 5. Staging Queries 5 & 6: `Stg_County` & `Stg_Mapping`

### `Stg_County`
```powerquery
let
    Source = Src_County,
    #"Renamed Columns" = Table.RenameColumns(
        Source,
        {
            {"subregion", "CountyName"},
            {"region", "StateName"},
            {"TotalUSD", "CountyTotalUSD"},
            {"MeanUSD", "CountyMeanUSD"},
            {"MedianUSD", "CountyMedianUSD"},
            {"TotalBackers", "CountyTotalBackers"},
            {"MeanBackers", "CountyMeanBackers"},
            {"MedianBackers", "CountyMedianBackers"}
        }
    ),
    #"Changed Types" = Table.TransformColumnTypes(
        #"Renamed Columns",
        {
            {"CountyName", type text},
            {"StateName", type text},
            {"CountyTotalUSD", Currency.Type},
            {"CountyMeanUSD", Currency.Type},
            {"CountyMedianUSD", Currency.Type},
            {"CountyTotalBackers", Int64.Type},
            {"CountyMeanBackers", type number},
            {"CountyMedianBackers", type number}
        }
    )
in
    #"Changed Types"
```

### `Stg_Mapping`
```powerquery
let
    Source = Src_Mapping,
    #"Renamed Columns" = Table.RenameColumns(
        Source,
        {
            {"State", "StateName"},
            {"Mean Campaign USD", "StateMeanUSD"},
            {"Projects Per", "StateProjectsCount"},
            {"Mean Bakers", "StateMeanBackers"},
            {"Total Pledged", "StateTotalPledgedUSD"},
            {"Total Backers", "StateTotalBackers"},
            {"Mean Days Building", "StateMeanBuildingDays"},
            {"Median Percent of Goal", "StateMedianPercentOfGoal"}
        }
    ),
    #"Changed Types" = Table.TransformColumnTypes(
        #"Renamed Columns",
        {
            {"StateName", type text},
            {"StateMeanUSD", Currency.Type},
            {"StateProjectsCount", Int64.Type},
            {"StateMeanBackers", type number},
            {"StateTotalPledgedUSD", Currency.Type},
            {"StateTotalBackers", Int64.Type},
            {"StateMeanBuildingDays", Int64.Type},
            {"StateMedianPercentOfGoal", Percentage.Type}
        }
    )
in
    #"Changed Types"
```
