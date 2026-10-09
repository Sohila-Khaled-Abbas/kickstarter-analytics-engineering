# 05 — DAX Semantic Layer & Measure Library Guide

## Enterprise DAX Semantic Layer & Business Logic

In an analytics engineering architecture, the **Semantic Layer** is where business concepts, KPIs, and analytical metrics are centralized. Instead of allowing report builders to write ad-hoc aggregations inside visual buckets, every calculation is standardized as a governed DAX measure.

---

## 1. Semantic Architecture & Display Folders

All DAX measures are consolidated inside a single dedicated disconnected table: `_Measures`.

### Creating the `_Measures` Table
In Power BI Desktop:
1. Navigate to **Home > Enter Data**.
2. Name the column `Metric` and the table `_Measures`.
3. Click **Load**.
4. Create your first measure in `_Measures`, then right-click the dummy column `Metric` and select **Hide** or **Delete**. Power BI will promote `_Measures` to a dedicated top-level calculator icon.

Inside `_Measures`, organize measures into **7 Display Folders**:
```text
_Measures
├── 📁 01 Core Portfolio & Counts
├── 📁 02 Success & Velocity Rates
├── 📁 03 Financials & Funding
├── 📁 04 Backer Dynamics
├── 📁 05 Geographic & Benchmark Indexes
├── 📁 06 Time Intelligence YoY & MoM
└── 📁 07 Goal Tiers & Distributions
```

---

## 2. Complete DAX Measure Library

### Folder 01: Core Portfolio & Counts

```dax
// Measure: Total Projects
Total Projects = 
DISTINCTCOUNT(Fact_Campaign[ProjectKey])
```

```dax
// Measure: Completed Projects
Completed Projects = 
CALCULATE(
    [Total Projects],
    KEEPFILTERS(Dim_Status[IsCompleted] = 1)
)
```

```dax
// Measure: Successful Projects
Successful Projects = 
CALCULATE(
    [Total Projects],
    KEEPFILTERS(Dim_Status[ProjectStatus] = "Successful")
)
```

```dax
// Measure: Failed Projects
Failed Projects = 
CALCULATE(
    [Total Projects],
    KEEPFILTERS(Dim_Status[ProjectStatus] = "Failed")
)
```

```dax
// Measure: Canceled Projects
Canceled Projects = 
CALCULATE(
    [Total Projects],
    KEEPFILTERS(Dim_Status[ProjectStatus] = "Canceled")
)
```

```dax
// Measure: Live Projects
Live Projects = 
CALCULATE(
    [Total Projects],
    KEEPFILTERS(Dim_Status[ProjectStatus] = "Live")
)
```

---

### Folder 02: Success & Velocity Rates

```dax
// Measure: Overall Success Rate %
Overall Success Rate % = 
DIVIDE(
    [Successful Projects],
    [Total Projects],
    0
)
```

```dax
// Measure: Completed Success Rate %
// Evaluates success only over campaigns whose funding window has closed
Completed Success Rate % = 
DIVIDE(
    [Successful Projects],
    [Completed Projects],
    0
)
```

```dax
// Measure: Failure Rate %
Failure Rate % = 
DIVIDE(
    [Failed Projects],
    [Completed Projects],
    0
)
```

```dax
// Measure: Average Campaign Duration (Days)
Average Campaign Duration (Days) = 
AVERAGE(Fact_Campaign[CampaignDurationDays])
```

```dax
// Measure: Median Campaign Duration (Days)
Median Campaign Duration (Days) = 
MEDIAN(Fact_Campaign[CampaignDurationDays])
```

---

### Folder 03: Financials & Funding

```dax
// Measure: Total Pledged USD
Total Pledged USD = 
SUM(Fact_Campaign[PledgedUSD])
```

```dax
// Measure: Total Goal USD
Total Goal USD = 
SUM(Fact_Campaign[GoalUSD])
```

```dax
// Measure: Overall Funding Ratio %
Overall Funding Ratio % = 
DIVIDE(
    [Total Pledged USD],
    [Total Goal USD],
    0
)
```

```dax
// Measure: Average Goal USD
Average Goal USD = 
AVERAGE(Fact_Campaign[GoalUSD])
```

```dax
// Measure: Median Goal USD
Median Goal USD = 
MEDIAN(Fact_Campaign[GoalUSD])
```

```dax
// Measure: Average Pledged USD
Average Pledged USD = 
AVERAGE(Fact_Campaign[PledgedUSD])
```

```dax
// Measure: Median Pledged USD
Median Pledged USD = 
MEDIAN(Fact_Campaign[PledgedUSD])
```

```dax
// Measure: Funded Surplus USD
// Surplus funds raised over and above the funding target for successful projects
Funded Surplus USD = 
SUMX(
    FILTER(Fact_Campaign, Fact_Campaign[PledgedUSD] > Fact_Campaign[GoalUSD]),
    Fact_Campaign[PledgedUSD] - Fact_Campaign[GoalUSD]
)
```

```dax
// Measure: Funding Gap USD
// Shortfall between target goal and pledged capital for failed campaigns
Funding Gap USD = 
SUMX(
    FILTER(Fact_Campaign, Fact_Campaign[GoalUSD] > Fact_Campaign[PledgedUSD]),
    Fact_Campaign[GoalUSD] - Fact_Campaign[PledgedUSD]
)
```

---

### Folder 04: Backer Dynamics

```dax
// Measure: Total Backers
Total Backers = 
SUM(Fact_Campaign[BackerCount])
```

```dax
// Measure: Average Backers per Campaign
Average Backers per Campaign = 
DIVIDE(
    [Total Backers],
    [Total Projects],
    0
)
```

```dax
// Measure: Median Backers
Median Backers = 
MEDIAN(Fact_Campaign[BackerCount])
```

```dax
// Measure: Average Pledge per Backer (USD)
Average Pledge per Backer (USD) = 
DIVIDE(
    [Total Pledged USD],
    [Total Backers],
    0
)
```

```dax
// Measure: High-Value Backer Density
// Ratio of pledge per backer relative to the category median
High-Value Backer Density = 
VAR OverallPPB = [Average Pledge per Backer (USD)]
VAR CategoryPPB = 
    CALCULATE(
        [Average Pledge per Backer (USD)],
        ALLSELECTED(Dim_Category)
    )
RETURN
DIVIDE(OverallPPB, CategoryPPB, 1)
```

---

### Folder 05: Geographic & Benchmark Indexes

```dax
// Measure: City Population
City Population = 
SUM(Fact_CityMetrics[CityPopulation])
```

```dax
// Measure: City All-Time Backers
City All-Time Backers = 
SUM(Fact_CityMetrics[CityAllTimeBackers])
```

```dax
// Measure: City Backer Penetration %
City Backer Penetration % = 
DIVIDE(
    [City All-Time Backers],
    [City Population],
    0
)
```

```dax
// Measure: State Benchmark Mean USD
State Benchmark Mean USD = 
AVERAGE(Dim_State_Metrics[Mean Campaign USD])
```

```dax
// Measure: State Success Rate %
State Success Rate % = 
CALCULATE(
    [Completed Success Rate %],
    USERELATIONSHIP(Fact_Campaign[LocationKey], Dim_Location[LocationKey])
)
```

```dax
// Measure: Geographic Performance Index
// Compares regional success rate against global baseline
Geographic Performance Index = 
VAR RegionSuccess = [Completed Success Rate %]
VAR GlobalSuccess = 
    CALCULATE(
        [Completed Success Rate %],
        ALL(Dim_Location)
    )
RETURN
DIVIDE(RegionSuccess, GlobalSuccess, 1)
```

---

### Folder 06: Time Intelligence YoY & MoM

```dax
// Measure: Pledged USD YoY (Year-over-Year Dollar Change)
Pledged USD YoY = 
VAR CurrentPledged = [Total Pledged USD]
VAR PriorYearPledged = 
    CALCULATE(
        [Total Pledged USD],
        SAMEPERIODLASTYEAR(Dim_Date[Date])
    )
RETURN
IF(
    ISBLANK(PriorYearPledged) || ISBLANK(CurrentPledged),
    BLANK(),
    CurrentPledged - PriorYearPledged
)
```

```dax
// Measure: Pledged USD YoY % (Year-over-Year Percentage Growth)
Pledged USD YoY % = 
VAR CurrentPledged = [Total Pledged USD]
VAR PriorYearPledged = 
    CALCULATE(
        [Total Pledged USD],
        SAMEPERIODLASTYEAR(Dim_Date[Date])
    )
RETURN
DIVIDE(
    CurrentPledged - PriorYearPledged,
    PriorYearPledged,
    BLANK()
)
```

```dax
// Measure: Projects Launched YoY %
Projects Launched YoY % = 
VAR CurrentCount = [Total Projects]
VAR PriorYearCount = 
    CALCULATE(
        [Total Projects],
        SAMEPERIODLASTYEAR(Dim_Date[Date])
    )
RETURN
DIVIDE(
    CurrentCount - PriorYearCount,
    PriorYearCount,
    BLANK()
)
```

```dax
// Measure: Rolling 12M Pledged USD
Rolling 12M Pledged USD = 
CALCULATE(
    [Total Pledged USD],
    DATESINPERIOD(
        Dim_Date[Date],
        MAX(Dim_Date[Date]),
        -12,
        MONTH
    )
)
```

```dax
// Measure: Pledged USD by Deadline Date
// Activates the role-playing inactive relationship between Fact_Campaign and Dim_Date
Pledged USD by Deadline Date = 
CALCULATE(
    [Total Pledged USD],
    USERELATIONSHIP(Fact_Campaign[DeadlineDateKey], Dim_Date[DateKey])
)
```

---

### Folder 07: Goal Tiers & Distributions

```dax
// Measure: Projects Micro Goal (<$1k)
Projects Micro Goal (<$1k) = 
CALCULATE(
    [Total Projects],
    KEEPFILTERS(Fact_Campaign[GoalUSD] < 1000)
)
```

```dax
// Measure: Projects Mid Goal ($1k-$10k)
Projects Mid Goal ($1k-$10k) = 
CALCULATE(
    [Total Projects],
    KEEPFILTERS(Fact_Campaign[GoalUSD] >= 1000 && Fact_Campaign[GoalUSD] < 10000)
)
```

```dax
// Measure: Projects High Goal ($10k-$100k)
Projects High Goal ($10k-$100k) = 
CALCULATE(
    [Total Projects],
    KEEPFILTERS(Fact_Campaign[GoalUSD] >= 10000 && Fact_Campaign[GoalUSD] < 100000)
)
```

```dax
// Measure: Projects Mega Goal (>$100k)
Projects Mega Goal (>$100k) = 
CALCULATE(
    [Total Projects],
    KEEPFILTERS(Fact_Campaign[GoalUSD] >= 100000)
)
```

```dax
// Measure: Mega Projects Success Rate %
Mega Projects Success Rate % = 
VAR MegaSuccessful = 
    CALCULATE(
        [Successful Projects],
        KEEPFILTERS(Fact_Campaign[GoalUSD] >= 100000)
    )
VAR MegaCompleted = 
    CALCULATE(
        [Completed Projects],
        KEEPFILTERS(Fact_Campaign[GoalUSD] >= 100000)
    )
RETURN
DIVIDE(MegaSuccessful, MegaCompleted, 0)
```

---

## 3. Formatting & Performance Best Practices

1. **Explicit Currency Formatting**: Set Format String for all USD measures to `$#,##0` or `$#,##0.00`.
2. **Explicit Percentage Formatting**: Set Format String for all rates to `0.0%` or `0.00%`.
3. **Always use DIVIDE**: Never use `/` for division. `DIVIDE(num, den, alt)` automatically handles division-by-zero safely without throwing engine exceptions.
4. **Use KEEPFILTERS**: When adding filter conditions inside `CALCULATE`, wrapping the predicate in `KEEPFILTERS()` ensures that external report slicer contexts are respected rather than overwritten.
