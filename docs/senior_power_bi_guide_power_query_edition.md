# Kickstarter Analytics: Power BI ETL Architecture Guide

As an Analytics Engineer doing the ETL directly inside Power BI, you are building a robust data pipeline using Power Query (M). Based on your architecture, we are dealing with three distinct "source families" that behave differently.

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

Here is your step-by-step playbook to ingest, harmonize, and model these sources.

---

## Phase 1: Ingestion & Staging (The 3 Source Families)

Your first goal is to create a "Staging" query for each of the three families. These queries will load and clean the raw data before we combine them.

### 1. MasterKickstarter (Historical Snapshot + Mapping)
This dataset represents a point-in-time snapshot but includes relational mapping tables.
*   **Action:** Go to **Get Data -> Text/CSV** and load `MasterKickstarter.csv`. Name the query `Staging_Master`.
*   **Action:** Load `County.csv` and `Mapping.csv` as well. 
*   **Transform:** You may need to perform a **Merge Queries** step inside Power Query to join the `Mapping.csv` data into `Staging_Master` so it has the full category or location names before we append everything together.

### 2. Kickstarter Projects (Historical Snapshots)
These are standard, mostly clean point-in-time CSVs from Kaggle (e.g., 2016 and 2018 datasets).
*   **Action:** Go to **Get Data -> Folder** and point it to your `raw/kickstarter_projects/` folder.
*   **Transform:** Click **Combine & Transform**. Power BI will stack the 2016 and 2018 datasets. Name this query `Staging_KaggleProjects`.

### 3. WebRobots (Recurring Crawls)
This is the messy, massive recurring data with embedded JSON.
*   **Action:** Go to **Get Data -> Folder** and point it to `data/raw/webrobots/` (where your Python script copied the files).
*   **Transform:** Click **Combine & Transform**. 
*   **Parse JSON:** Select the `category` column. Go to the **Transform** tab -> **Parse** -> **JSON**. Click the expand icon `<- ->` at the top of the column to extract `name` (Subcategory) and `slug` (Parent Category).
*   Name this query `Staging_WebRobots`.

---

## Phase 2: Schema Harmonization

Before you can stack these three families into a single table, their columns must match *perfectly* (case-sensitive).

1.  **Add Lineage:** In each of the three staging queries, go to **Add Column -> Custom Column**. Name it `Source_Family`. 
    *   For Staging_Master, enter `"MasterKickstarter"`.
    *   For Staging_KaggleProjects, enter `"KaggleProjects"`.
    *   For Staging_WebRobots, enter `"WebRobots"`.
2.  **Rename Columns:** Ensure the core columns share the exact same names across all three queries (e.g., `project_id`, `name`, `state`, `launched_at`, `deadline_at`, `pledged_usd`, `goal_usd`, `category_name`, `country`).
3.  **Delete Extra Columns:** Remove any columns that don't exist in all three datasets or that you don't need for analysis.

---

## Phase 3: Integration & Append

Now we bring the families together.

1.  On the Home tab, click **Append Queries -> Append Queries as New**.
2.  Select **Three or more tables**.
3.  Add `Staging_Master`, `Staging_KaggleProjects`, and `Staging_WebRobots` to the append list.
4.  Name this new query `Fact_Campaigns_Raw`.
5.  *Crucial:* Right-click your three original staging queries and **uncheck "Enable Load"**. You only want the final appended table to load into the VertiPaq engine.

---

## Phase 4: Advanced Deduplication (The Golden Rule)

Because WebRobots crawls the same campaigns monthly, and Kaggle snapshots overlap with WebRobots, you have massive duplication. You *must* get the absolute latest state of the campaign (e.g., when it finally changed to "successful").

The standard "Remove Duplicates" UI button often fails in the Power BI Service because the Mashup Engine reorders rows to optimize performance. You must force the engine to respect your sort order using `Table.Buffer`.

**The Bulletproof M Code Approach for Deduplication:**

1. Select `Fact_Campaigns_Raw`.
2. Open the **Advanced Editor** from the Home tab.
3. Adjust the final steps of your script to look like this:

```powerquery
    // ... previous steps (like your Append) ...
    
    // 1. Sort the table by your date/timestamp column Descending (Newest data first)
    SortedRows = Table.Sort(PreviousStepName,{{"launched_at", Order.Descending}, {"Source_Family", Order.Descending}}),
    
    // 2. Buffer the table in memory. This FORCES the engine to respect the sort.
    BufferedTable = Table.Buffer(SortedRows),
    
    // 3. Remove duplicates based on the Project ID, keeping the top (newest) row
    Deduplicated = Table.Distinct(BufferedTable, {"project_id"})
in
    Deduplicated
```

## Phase 5: Dimensional Modeling

Do not load this massive flat table directly into your dashboard. Build a Star Schema.

1.  **Dimensions:** Right-click `Fact_Campaigns_Raw` and select **Reference**. Name it `Dim_Category`. Remove all columns except the category names. Remove duplicates. Add an Index column (`category_id`). Repeat this for `Dim_Location`.
2.  **Fact Table:** Go back to `Fact_Campaigns_Raw`. Do a **Merge Queries** to bring in the `category_id` and `location_id`. Then, delete the text-based category and location columns to save massive amounts of RAM.

You now have a highly optimized, fully deduplicated analytical model combining historical snapshots and recurring crawls!