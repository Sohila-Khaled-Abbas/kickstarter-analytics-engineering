# Kickstarter Analytics: Advanced Power Query (M) Playbook

As an Analytics Engineer, building a robust data pipeline directly inside Power BI requires mastering both the Power Query Graphical User Interface (GUI) and the underlying M language.

Because we are dealing with three distinct source families with massive temporal overlaps, standard point-and-click transformations will not be enough. This guide walks you step-by-step through staging, harmonizing, deduplicating, and modeling your data using Advanced Power Query techniques.

```
                    KICKSTARTER ANALYTICS
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
 MasterKickstarter  Kickstarter Projects    WebRobots
  source family       source family       source family
        │                   │                   │
        ▼                   ▼                   ▼
   Historical          Historical           Recurring
   snapshot +          snapshots             crawls
 mapping tables 

```

## Phase 1: Data Ingestion & Staging (GUI + M Code)

Our first goal is to create a "Staging" query for each of the three families. These queries load and pre-clean the raw data. **Do not load these directly to the report; we will disable their load later.**

### 1. Staging_Master & Auxiliary Tables (Historical Snapshot)

* **GUI Steps for Master:**

  1. Click **Get Data -> Text/CSV** and load `data/raw/master_kickstarter/MasterKickstarter.csv`. Name it `Staging_Master`.

  2. Repeat the process to load `County.csv` (Name it `Staging_County`).

  3. Select `Staging_Master`. Go to **Home -> Merge Queries**.

  4. Select `Staging_County` in the dropdown. Match the geographic ID/Name column in your Master table to the corresponding column in the County table to extract richer location names if they are missing from the Master file.

* **Handling Mapping.csv (State Aggregations):**

  1. Click **Get Data -> Text/CSV** and load `Mapping.csv`. Name it `Dim_State_Metrics`.

  2. **CRITICAL:** Do *not* merge this into `Staging_Master`. Because this file contains pre-aggregated data (`Mean Campaign USD`, `Projects Per`, `Total Backers`), it has a different **granularity** than your campaign-level data. We will keep this as a separate table and link it in the Data Model view later.

### 2. Staging_KaggleProjects (Historical Snapshots)

These are standard, mostly clean point-in-time CSVs.

* **GUI Steps:**

  1. Click **Get Data -> Folder**. Browse to `data/raw/kickstarter_projects/`.

  2. Click **Combine & Transform Data**. Power BI automatically generates a helper function to stack the files.

  3. Name the resulting query `Staging_KaggleProjects`.

  4. Remove any automatically generated columns you don't need (like `Source.Name`).

### 3. Staging_WebRobots (Recurring JSON/CSV Crawls)

This is the messy, massive recurring data with embedded JSON arrays.

* **GUI Steps:**

  1. Click **Get Data -> Folder**. Browse to `data/raw/webrobots/`.

  2. Click **Combine & Transform Data**. Name the query `Staging_WebRobots`.

  3. **The JSON Challenge:** Find the `category` column. Right-click -> **Transform -> JSON**. Extract `name` (Subcategory) and `slug` (Parent Category).

  4. Repeat for the `location` column to extract country and state/city information so it matches the granularity of your `County.csv` data!

* **Senior BI Pro-Tip:** The GUI can sometimes struggle with millions of rows of JSON parsing. Use this custom M code in the Advanced Editor to parse safely:

  ```
  // Safely parse Category JSON
  ParsedCategory = Table.AddColumn(PreviousStep, "Category_Parsed", each try Json.Document([category]) otherwise null),
  ExpandedCategory = Table.ExpandRecordColumn(ParsedCategory, "Category_Parsed", {"name", "slug"}, {"subcategory_name", "category_slug"}),
  
  // Safely parse Location JSON
  ParsedLocation = Table.AddColumn(ExpandedCategory, "Location_Parsed", each try Json.Document([location]) otherwise null),
  ExpandedLocation = Table.ExpandRecordColumn(ParsedLocation, "Location_Parsed", {"country", "state", "displayable_name"}, {"country", "state", "city"})
  
  ```

## Phase 2: Schema Harmonization

Before appending, the columns in all three staging queries must match *perfectly* (case-sensitive names and data types).

1. **Add Lineage:** Go to **Add Column -> Custom Column**. Name it `Source_Family`. Enter `"MasterKickstarter"`, `"KaggleProjects"`, or `"WebRobots"` respectively.

2. **Standardize Column Names:** Ensure core columns align: `project_id`, `name`, `status`/`state`, `launched_at`, `deadline_at`, `pledged_usd`, `goal_usd`, `category_name`, `country`, `state`. *(Note: Be careful not to confuse campaign `state` \[live/failed\] with geographic `state` \[NY/CA\]. Rename them `campaign_status` and `geo_state` if necessary).*

3. **Data Types:** Ensure `launched_at` and `deadline_at` are set to **Date/Time**, and `pledged_usd` is a **Decimal Number**.

## Phase 3: Integration & Append

Now we stack the families into a single, massive table.

1. **GUI Steps:**

   * On the Home tab, click **Append Queries -> Append Queries as New**.

   * Select **Three or more tables**.

   * Add `Staging_Master`, `Staging_KaggleProjects`, and `Staging_WebRobots`.

   * Name this new query `Fact_Campaigns_Raw`.

2. **Memory Management (CRITICAL):**

   * Right-click `Staging_Master`, `Staging_County`, `Staging_KaggleProjects`, and `Staging_WebRobots` and **uncheck "Enable Load"**. (Leave `Dim_State_Metrics` enabled).

## Phase 4: Advanced Deduplication (`Table.Buffer`)

Because WebRobots crawls the same campaigns monthly, and Kaggle overlaps with WebRobots, you have massive row duplication. You *must* get the absolute latest state of the campaign.

* **M Code (Advanced Editor):**
  Open the Advanced Editor for `Fact_Campaigns_Raw` and add this exact logic to the end:

  ```
      // 1. Sort Descending by Date and Source Family (WebRobots is generally newer)
      SortedRows = Table.Sort(PreviousStepName,{{"launched_at", Order.Descending}, {"Source_Family", Order.Descending}}),
  
      // 2. Buffer the table in memory. This creates a hard stop and FORCES the engine to respect the sort order above.
      BufferedTable = Table.Buffer(SortedRows),
  
      // 3. Remove duplicates based on Project ID. Because it's sorted descending, it keeps the top (newest) row!
      Deduplicated = Table.Distinct(BufferedTable, {"project_id"})
  in
      Deduplicated
  
  ```

## Phase 5: Dimensional Modeling (Star Schema)

Do not load a 50-column flat table into your report. VertiPaq thrives on narrow Fact tables and distinct Dimension tables.

### 1. Create `Dim_Category`

1. Right-click `Fact_Campaigns_Raw` -> **Reference**. Name it `Dim_Category`.

2. Select *only* `category_name` and `subcategory_name`. **Remove Other Columns**.

3. **Remove Duplicates** and add an **Index Column** named `category_id`.

### 2. Create `Dim_Location`

1. Right-click `Fact_Campaigns_Raw` -> **Reference**. Name it `Dim_Location`.

2. Select your geographic columns (`country`, `geo_state`, `city`). **Remove Other Columns**.

3. **Remove Duplicates** and add an **Index Column** named `location_id`.

### 3. Finalize `Fact_Campaigns`

1. Right-click `Fact_Campaigns_Raw` -> **Reference**. Name it `Fact_Campaigns`.

2. **Home -> Merge Queries**. Merge with `Dim_Category` and `Dim_Location` to extract `category_id` and `location_id`.

3. Delete the heavy text columns (`category_name`, `country`, `geo_state`) from the Fact table.

4. Right-click `Fact_Campaigns_Raw` and **uncheck "Enable Load"**.

### Phase 6: The Model View (Snowflaking)

When you click **Close & Apply**, go to the Model View in Power BI:

1. Link `Dim_Category[category_id]` -> `Fact_Campaigns[category_id]`.

2. Link `Dim_Location[location_id]` -> `Fact_Campaigns[location_id]`.

3. **The Mapping.csv connection:** Link `Dim_State_Metrics[State]` -> `Dim_Location[geo_state]`.

By linking the pre-calculated `Mapping.csv` data to your Location dimension instead of the Fact table, you've created a perfect "Snowflake" schema that won't duplicate your metrics!