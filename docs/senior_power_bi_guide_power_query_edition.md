# Kickstarter Analytics: Advanced Power Query (M) Playbook

As an Analytics Engineer, building a robust data pipeline directly inside Power BI requires mastering both the Power Query Graphical User Interface (GUI) and the underlying M language.

Because we are dealing with three distinct source families with massive temporal overlaps, standard point-and-click transformations will not be enough. This guide walks you step-by-step through staging, harmonizing, deduplicating, and modeling your data using Advanced Power Query techniques.

```text
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

### 1. Staging_Master (Historical Snapshot + Mapping + County)

This dataset is highly normalized. It uses `Mapping.csv` for categories and `County.csv` for geographic data. We need to flatten this out before appending it to the other sources.

* **GUI Steps:**
  1. Click **Get Data -> Text/CSV** and load `data/raw/master_kickstarter/MasterKickstarter.csv`. Name it `Staging_Master`.
  2. Repeat the process to load `Mapping.csv` (Name it `Staging_Mapping`) and `County.csv` (Name it `Staging_County`).
  3. Select `Staging_Master`. Go to **Home -> Merge Queries**.
  4. Select `Staging_Mapping` in the bottom dropdown. Click the category ID columns in both tables to join them (Left Outer). Extract the `category_name`.
  5. Go to **Merge Queries** again. This time select `Staging_County`. Match the geographic ID column (e.g., `county_id` or `location_id`) in your Master table to the ID in the County table. Extract the location names (e.g., `country`, `state`, `county`).

* **M Code (Advanced Editor) equivalent:**
  ```powerquery
  let
      Source = Csv.Document(File.Contents("D:\...\data\raw\master_kickstarter\MasterKickstarter.csv"),[Delimiter=",", Columns=15, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
      PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
      
      // Join Category Mapping
      MergedCategory = Table.NestedJoin(PromotedHeaders, {"category_id"}, Staging_Mapping, {"id"}, "Mapping", JoinKind.LeftOuter),
      ExpandedCategory = Table.ExpandTableColumn(MergedCategory, "Mapping", {"category_name"}, {"category_name"}),

      // Join Geographic (County) Mapping
      MergedCounty = Table.NestedJoin(ExpandedCategory, {"county_id"}, Staging_County, {"id"}, "CountyData", JoinKind.LeftOuter),
      ExpandedCounty = Table.ExpandTableColumn(MergedCounty, "CountyData", {"country", "state", "county"}, {"country", "state", "county"})
  in
      ExpandedCounty
  ```

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
  3. **The JSON Challenge:** Find the `category` column (it looks like a text string of JSON). Right-click the column header -> **Transform -> JSON**.
  4. Click the expand icon `<- ->` to extract `name` (Subcategory) and `slug` (Parent Category).
  5. Do the same for the `location` column to extract country and state/city information to match your `County.csv` detail level!

* **Senior BI Pro-Tip:** The GUI can sometimes struggle with millions of rows of JSON parsing. If it's slow, use this custom M code for the column:
  ```powerquery
  // Add a custom column to safely parse the JSON text
  ParsedCategory = Table.AddColumn(PreviousStep, "Category_Parsed", each try Json.Document([category]) otherwise null),
  ExpandedCategory = Table.ExpandRecordColumn(ParsedCategory, "Category_Parsed", {"name", "slug"}, {"subcategory_name", "category_slug"}),
  
  ParsedLocation = Table.AddColumn(ExpandedCategory, "Location_Parsed", each try Json.Document([location]) otherwise null),
  ExpandedLocation = Table.ExpandRecordColumn(ParsedLocation, "Location_Parsed", {"country", "state", "displayable_name"}, {"country", "state", "city"})
  ```

## Phase 2: Schema Harmonization

Before appending, the columns in all three staging queries must match *perfectly* (case-sensitive names and data types).

1. **Add Lineage:** Go to **Add Column -> Custom Column**. Name it `Source_Family`. Enter `"MasterKickstarter"`, `"KaggleProjects"`, or `"WebRobots"` respectively.
2. **Standardize Column Names:** Ensure core columns align: `project_id`, `name`, `state`, `launched_at`, `deadline_at`, `pledged_usd`, `goal_usd`, `category_name`, `country`, `state`.
3. **Data Types:** Ensure `launched_at` and `deadline_at` are set to **Date/Time**, and `pledged_usd` is a **Decimal Number**.

## Phase 3: Integration & Append

Now we stack the families into a single, massive table.

1. **GUI Steps:**
   * On the Home tab, click **Append Queries -> Append Queries as New**.
   * Select **Three or more tables**.
   * Add `Staging_Master`, `Staging_KaggleProjects`, and `Staging_WebRobots`.
   * Name this new query `Fact_Campaigns_Raw`.
2. **Memory Management (CRITICAL):**
   * Right-click `Staging_Master`, `Staging_Mapping`, `Staging_County`, `Staging_KaggleProjects`, and `Staging_WebRobots` in the left pane and **uncheck "Enable Load"**.
   * *Why?* You only want the final appended table loaded into VertiPaq. Loading the staging tables duplicates your RAM usage.

## Phase 4: Advanced Deduplication (`Table.Buffer`)

Because WebRobots crawls the same campaigns monthly, and Kaggle overlaps with WebRobots, you have massive row duplication. You *must* get the absolute latest state of the campaign.

**The standard "Remove Duplicates" UI button often fails in the Power BI Service** because the Mashup Engine reorders rows in the background to optimize memory, breaking your sort order. You must force the engine to respect your sort using `Table.Buffer`.

* **M Code (Advanced Editor):**
  Open the Advanced Editor for `Fact_Campaigns_Raw`. Replace the final steps of your script with this exact logic:
  ```powerquery
      // ... previous steps (like your Append) ...
  
      // 1. Sort Descending by Date and Source Family (WebRobots is generally newer than Kaggle)
      SortedRows = Table.Sort(PreviousStepName,{{"launched_at", Order.Descending}, {"Source_Family", Order.Descending}}),
  
      // 2. Buffer the table in memory. This creates a hard stop and FORCES the engine to respect the sort order above.
      BufferedTable = Table.Buffer(SortedRows),
  
      // 3. Remove duplicates based on Project ID. Because it's sorted descending, it keeps the top (newest) row!
      Deduplicated = Table.Distinct(BufferedTable, {"project_id"})
  in
      Deduplicated
  ```

## Phase 5: Dimensional Modeling (Star Schema)

Do not load a 50-column flat table into your report. VertiPaq thrives on narrow Fact tables and distinct Dimension tables (Star Schema).

### 1. Create `Dim_Category`
1. Right-click `Fact_Campaigns_Raw` -> **Reference**. Name it `Dim_Category`.
2. Select *only* `category_name` and `subcategory_name`. Right-click header -> **Remove Other Columns**.
3. Select both columns -> **Remove Duplicates**.
4. Go to **Add Column -> Index Column (From 1)**. Name it `category_id`.

### 2. Create `Dim_Location`
1. Right-click `Fact_Campaigns_Raw` -> **Reference**. Name it `Dim_Location`.
2. Select your geographic columns (`country`, `state`, `county`/`city`). **Remove Other Columns**.
3. **Remove Duplicates**.
4. Add an **Index Column** named `location_id`.

### 3. Finalize `Fact_Campaigns`
Now we replace the heavy text columns in the Fact table with the lightweight integer IDs from our new dimensions.

1. Right-click `Fact_Campaigns_Raw` -> **Reference**. Name it `Fact_Campaigns`.
2. **Home -> Merge Queries**. Merge with `Dim_Category` matching on category names. Extract only `category_id`.
3. Merge with `Dim_Location` matching on geography. Extract only `location_id`.
4. **Crucial Cleanup:** Delete the text columns `category_name`, `subcategory_name`, `country`, `state`, and `county` from `Fact_Campaigns`.
5. Right-click `Fact_Campaigns_Raw` and **uncheck "Enable Load"**.

### The Result
When you click **Close & Apply**, Power BI will only load `Fact_Campaigns`, `Dim_Category`, and `Dim_Location`. Go to the Model View, link the IDs, and you have built a highly optimized, dynamically deduplicated Analytics Engineering pipeline!