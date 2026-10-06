# Phase 2: Power Query Source Ingestion & Staging

**Objective:** Cleanse, type-cast, and normalize individual datasets before they are merged.

## 1. Kaggle 2018 (`Stg_Kaggle_2018`)
This is the baseline historical dataset containing 15 attributes.

*   **Rename Columns:** `ID` -> `ProjectID`, `name` -> `ProjectName`, `category` -> `Subcategory`, `main_category` -> `Category`, `usd_pledged_real` -> `PledgedUSD`, `usd_goal_real` -> `GoalUSD`, `pledged` -> `PledgedLocal`, `goal` -> `GoalLocal`.
*   **Text Cleaning:** Apply `Text.Trim()` and `Text.Clean()` to all text columns. Apply `Text.Lower()` to `ProjectStatus`.
*   **Feature Engineering:** Calculate duration safely to flag bad data.
    ```powerquery
    = Table.AddColumn(PreviousStep, "DurationDays", each Duration.Days([DeadlineDateTime] - [LaunchDateTime]), Int64.Type)
    ```

## 2. Kaggle 2016 (`Stg_Kaggle_2016`)
This file is known for structural and encoding issues.

*   **Encoding:** When connecting to the CSV, manually set the Origin (Encoding) to `Windows-1252` (or Code Page 1252) to prevent character corruption.
*   **Column Cleanup:** Delete `Unnamed: 13`, `Unnamed: 14`, etc.
*   **Currency Logic:** This file lacks `usd_goal_real`. **Do not** fake precision.
    ```powerquery
    GoalUSD = if [CurrencyCode] = "USD" then [GoalLocal] else null
    ```

## 3. MasterKickstarter (`Stg_MasterKickstarter`)
This dataset contains ~57 columns, heavily enriched with geographic data.

*   **Text Normalization:** Fix inconsistent casing.
    ```powerquery
    = Table.TransformColumns(PreviousStep,{{"State", each Text.Proper(Text.Trim(_)), type text}})
    ```
*   **Split the Grain:** This table contains both campaign data and city/state metrics. Keep Campaign-level data (`ProjectID`, `Status`) in this staging query. Move aggregate columns (`City_Pop`, `Mean_Backers`) to a separate staging query (`Stg_CityMetrics`). Do not mix them!

## 4. WebRobots (`Stg_WebRobots`)
This is the monthly recurring snapshot dataset.

*   **Extract Snapshot Date:** The date the crawl occurred is trapped in the filename (e.g., `Kickstarter_2023-05-18.csv`).
    *   Extract it using `Text.BetweenDelimiters([Source.Name], "Kickstarter_", ".")`.
*   **Convert Unix Timestamps:** Convert `launched_at`, `deadline`, and `state_changed_at` from Unix integers to standard Date/Time.
    ```powerquery
    = Table.AddColumn(PreviousStep, "LaunchDateTime", each #datetime(1970,1,1,0,0,0) + #duration(0,0,0,[launched_at]))
    ```
*   **Parse JSON:** The `category` and `location` columns are JSON strings.
    *   Transform -> Parse -> JSON.
    *   Expand `category` to extract `id`, `name`, `slug`.
    *   Expand `location` to extract `country`, `state`, `displayable_name`.