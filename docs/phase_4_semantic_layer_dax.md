# Phase 4: Semantic Layer & DAX Measures

**Objective:** Configure table relationships and define enterprise DAX measures for analytics.

## 1. Relationship Architecture (Model View)
1.  **Cardinality:** All relationships must be **One-to-Many (1:*)**.
2.  **Cross-Filter Direction:** Set all to **Single**. The Dimension filters the Fact.
3.  **No Direct Fact-to-Fact Links:** `Fact_Campaign` and `Fact_CampaignSnapshot` must never be connected directly. They communicate exclusively by filtering the same shared Dimensions (e.g., `Dim_Category`).

## 2. Role-Playing Dates
A campaign has multiple relevant dates (Launch, Deadline, Snapshot).
*   Connect `Dim_Date[DateKey]` to `Fact_Campaign[LaunchDateKey]` -> **Active** relationship.
*   Connect `Dim_Date[DateKey]` to `Fact_Campaign[DeadlineDateKey]` -> **Inactive** relationship.
*   *Note: Use `USERELATIONSHIP()` in DAX when analyzing by deadline, or create a separate `Dim_DeadlineDate` table.*

## 3. Core DAX Measures
Create a separate table named `_Measures` to house all business logic.

**Portfolio Measures:**
```dax
Total Projects = DISTINCTCOUNT(Fact_Campaign[ProjectKey])

Total Pledged USD = SUM(Fact_Campaign[PledgedUSD])

Total Goal USD = SUM(Fact_Campaign[GoalUSD])

Total Backers = SUM(Fact_Campaign[BackerCount])

Funding Ratio = DIVIDE([Total Pledged USD], [Total Goal USD], 0)
```

**Governed Success Logic:**
Instead of hardcoding `"successful"` in every chart, use the `Dim_Status` table.
```dax
Completed Projects = CALCULATE([Total Projects], Dim_Status[IsCompleted] = 1)

Successful Projects = CALCULATE([Total Projects], Dim_Status[Status] = "successful")

Completed Success Rate = DIVIDE([Successful Projects], [Completed Projects], 0)
```

**Snapshot / Time-Series Analytics:**
Leveraging the WebRobots Fact table to track historical platform health.
```dax
Snapshot Pledged USD = SUM(Fact_CampaignSnapshot[PledgedUSD])

Previous Snapshot Pledged = 
CALCULATE(
    [Snapshot Pledged USD],
    DATEADD(Dim_Date[Date], -1, MONTH)
)

Pledged Growth = [Snapshot Pledged USD] - [Previous Snapshot Pledged]

Pledged Growth % = DIVIDE([Pledged Growth], [Previous Snapshot Pledged], 0)
```

## 4. UI Polish
Select all `*Key` columns (e.g., `ProjectKey`, `CategoryKey`) in all Fact tables, right-click, and select **Hide in report view**. Report authors should only ever filter using the descriptive text columns located in the Dimension tables.