# Phase 5: Quality Assurance & Reporting

**Objective:** Audit the integrity of the data model and design a storytelling-driven dashboard.

## 1. QA Queries (Power Query)
Inside the `99 QA` folder, build diagnostic queries to ensure your data engineering is flawless. These queries should ideally return zero rows.

*   **QA_DuplicateProjects:**
    Reference `Fact_Campaign`. Group by `ProjectKey`, count the rows, and filter for `Count > 1`.
*   **QA_DuplicateSnapshots:**
    Reference `Fact_CampaignSnapshot`. Group by `ProjectKey` AND `SnapshotDateKey`, count rows, filter for `Count > 1`.
*   **QA_OrphanKeys:**
    Filter `Fact_Campaign[LocationKey]` or `[CategoryKey]` for `null`.
*   **QA_ValueChecks:**
    Filter `Fact_Campaign` for impossible scenarios: `CampaignDurationDays < 0`, `GoalUSD < 0`, or `PledgedUSD < 0`. Don't automatically delete these; flag them for investigation.

## 2. Report Design & Narrative
Structure your dashboard to answer specific analytical questions progressively.

### Page 1: Executive Overview
*   **Questions:** What is the overall health of the portfolio?
*   **Visuals:** KPI Cards (Total Projects, Success Rate, Total Pledged). Line charts of Projects by Launch Year.

### Page 2: Campaign Performance
*   **Questions:** What factors drive a campaign to succeed or fail?
*   **Visuals:** Scatter plot comparing Campaign Duration vs. Funding Ratio. Matrix of Success Rates by Subcategory.

### Page 3: Geographic Intelligence
*   **Questions:** Where does Kickstarter funding come from?
*   **Visuals:** Filled maps using `Dim_Location`. Scatter plot comparing City Population (`Fact_CityMetrics`) vs. Total Backers to identify localized organic reach.

### Page 4: Snapshot Lifecycle (WebRobots)
*   **Questions:** How do campaigns trend during their active month?
*   **Visuals:** Area chart showing `Snapshot Pledged USD` month-over-month. Line chart showing `MoM Pledged Growth %`.

### Page 5: Data Quality (Developer Page)
*   **Questions:** Can we trust the data?
*   **Visuals:** Cards showing rows dropped during deduplication, null key counts, and the latest data refresh timestamp. Hide this page from end-users.