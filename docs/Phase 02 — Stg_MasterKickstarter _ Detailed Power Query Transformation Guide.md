# `Stg_MasterKickstarter` — Detailed Power Query Transformation Phase

`MasterKickstarter.csv` is a richer enrichment dataset than the Kaggle 2016/2018 campaign files. It contains campaign-level attributes plus location, coordinates, population, and pre-calculated city/year/month analytical features. The source contains approximately 99,000 Kickstarter projects spanning 2009–2017 with 57 attributes.

The purpose of `Stg_MasterKickstarter` is therefore **not** to immediately turn all 57 columns into one fact table.

Instead, this staging query will:

1. Clean the raw Master dataset.
2. Standardize campaign columns to the canonical Kickstarter schema.
3. Standardize dates and numeric fields.
4. Preserve useful geographic enrichment.
5. Preserve source-derived analytical features temporarily for validation.
6. Prepare the data to be split later into:
   - campaign/conformed data,
   - location dimensions,
   - city-level metrics,
   - geographic aggregate facts.

`Stg_MasterKickstarter` must remain a **staging query** with **Enable Load disabled**.

---

# 1. Raw Columns

The source contains:

```text
X1
X1_1
Country
City
id
name
blurb
goal
pledged
status
slug
disable_communication
currency
currency_symbol
currency_trailing_code
deadline
state_changed_at
created_at
launched_at
staff_pick
backers_count
deadlineTime
state_changed_atTime
created_atTime
launched_atTime
Categories
spotLight
pledgedUSD
Ex_USd
deadlineYM
state_changed_atYM
created_atYM
launched_atYM
deadlineY
state_changed_atY
created_atY
launched_atY
Pledge_per_person
Prct_goal
Length_of_kick
City_Pop
Latitude
Longitude
County
State
Backers_as_Prct_of_Pop
Backers_as_Prct_of_Pop_YM
Backers_as_Prct_of_Pop_Y
Days_spent_making_campign
Days_inception_to_Deadline
Backers_in_city_Y
Backers_in_city_YM
All_Time_Backers_city
Mean_Pledge_City
Mean_pledge_city_Y
Mean_pledge_city_YM
```

The source's published analysis confirms that `Categories` is used as the campaign category field and that city-level metrics such as `All_Time_Backers_city` and geographic/state metrics are part of the analytical dataset.

---

# 2. Remove Technical Index Columns

The first transformation should be removal of:

```text
X1
X1_1
```

These are technical/index-style columns and should not become business attributes or model keys.

Go to:

**Home → Remove Columns → Remove Columns**

Select:

```text
X1
X1_1
```

Do this before any downstream references are created.

---

# 3. Standardize Campaign Identifier

Rename:

```text
id
```

to:

```text
ProjectID
```

Recommended data type:

```text
Int64 / Whole Number
```

This is the natural business identifier for the Kickstarter campaign.

Do **not** use `X1` or `X1_1` as the project key.

---

# 4. Standardize Campaign Text Fields

Rename:

```text
name
```

to:

```text
ProjectName
```

Rename:

```text
blurb
```

to:

```text
Blurb
```

Rename:

```text
slug
```

to:

```text
ProjectSlug
```

These should be:

```text
Text
```

---

# 5. Clean Campaign Text

For:

```text
ProjectName
Blurb
ProjectSlug
Country
City
County
State
Categories
status
currency
currency_symbol
```

apply:

```powerquery
Text.Trim(Text.Clean(_))
```

For a specific column, for example `City`:

```powerquery
Text.Trim(Text.Clean([City]))
```

This prevents values such as:

```text
" New York "
"New York"
"New York  "
```

from becoming separate dimension members.

---

# 6. Standardize the Category Field

The Master dataset does **not** provide separate `Category` and `Subcategory` columns. It provides:

```text
Categories
```

The original analysis treats `Categories` as a categorical field, including the major campaign categories used in the visualization.

Therefore create:

```text
Category
```

from:

```text
Categories
```

Use:

**Add Column → Custom Column**

```powerquery
if [Categories] = null or Text.Trim(Text.From([Categories])) = ""
then null
else Text.Trim(Text.Clean(Text.From([Categories])))
```

Recommended name:

```text
Category
```

### `Subcategory`

Do **not** invent a subcategory from this dataset.

Because the provided Master schema contains no separate subcategory column, use:

```text
Subcategory = null
```

or handle the unavailable level later in `Dim_Category`.

For example:

```powerquery
if [Category] = null then null else null
```

You may eventually create a dimension row such as:

```text
Subcategory = "Not Available"
```

for Master-only records, but do not pretend that the dataset contains a real subcategory.

---

# 7. Standardize Project Status

Rename:

```text
status
```

to:

```text
ProjectStatus
```

Then normalize:

```powerquery
if [ProjectStatus] = null
then null
else Text.Lower(Text.Trim(Text.Clean(Text.From([ProjectStatus]))))
```

This gives consistent values such as:

```text
canceled
failed
live
successful
suspended
```

The original analysis specifically uses these campaign status categories.

---

# 8. Standardize Currency

Rename:

```text
currency
```

to:

```text
CurrencyCode
```

Rename:

```text
currency_symbol
```

to:

```text
CurrencySymbol
```

Rename:

```text
currency_trailing_code
```

to:

```text
CurrencyTrailingCode
```

Recommended types:

```text
CurrencyCode          → Text
CurrencySymbol        → Text
CurrencyTrailingCode  → Logical / Text depending on actual source type
```

Do not convert currencies in this staging query unless you have a validated exchange-rate definition.

---

# 9. Goal and Pledged Amounts

Rename:

```text
goal
```

to:

```text
GoalLocal
```

Rename:

```text
pledged
```

to:

```text
PledgedLocal
```

Set both to:

```text
Decimal Number
```

Create them using safe numeric conversion if the source is not already numeric:

```powerquery
try Number.From([goal]) otherwise null
```

and:

```powerquery
try Number.From([pledged]) otherwise null
```

---

# 10. Use the Existing `pledgedUSD`

The Master dataset already provides:

```text
pledgedUSD
```

Rename it to:

```text
PledgedUSD
```

Then:

```powerquery
try Number.From([PledgedUSD]) otherwise null
```

Set the final type to:

```text
Decimal Number
```

Do **not** calculate `PledgedUSD` from `pledged` yourself when the source already supplies a USD-normalized field.

---

# 11. `Ex_USd`

The source also contains:

```text
Ex_USd
```

Because the provided schema does not give us a formal data dictionary definition for this field, do **not** automatically use it as an exchange rate in your canonical conversion logic.

For now:

```text
Ex_USd
```

should be retained temporarily in staging for profiling/validation.

Give it a provisional technical name only after inspecting its values, for example:

```text
ExchangeRateCandidate
```

Do not build financial calculations from it until its meaning and direction are verified.

Your canonical USD fields should continue to rely on:

```text
PledgedUSD
```

rather than reverse-engineering the source's FX logic.

---

# 12. Backers

Rename:

```text
backers_count
```

to:

```text
BackerCount
```

Convert safely:

```powerquery
try Number.From([BackerCount]) otherwise null
```

Set:

```text
Whole Number
```

---

# 13. Campaign Date Fields

The dataset contains:

```text
deadline
state_changed_at
created_at
launched_at
```

and also:

```text
deadlineTime
state_changed_atTime
created_atTime
launched_atTime
```

plus pre-derived:

```text
deadlineYM
state_changed_atYM
created_atYM
launched_atYM
deadlineY
state_changed_atY
created_atY
launched_atY
```

Do **not** load every one of these into the final model.

The staging layer should first determine which are the actual date/date-time representations.

The canonical campaign dates should become:

```text
CreatedDateTime
LaunchDateTime
DeadlineDate
StateChangedDateTime
```

---

# 14. Canonical `DeadlineDate`

Because your project is using Deadline as a **Date**, standardize it as:

```text
DeadlineDate
```

If the existing `deadline` column is already a date:

```powerquery
Date.From([deadline])
```

If the usable value is instead contained in `deadlineTime`, first inspect its actual type before converting.

The final analytical column should be:

```text
DeadlineDate
```

with data type:

```text
Date
```

Do not create `DeadlineDateTime` in the final canonical schema if your dataset only needs the deadline date.

---

# 15. Canonical Launch Date

For campaign-level date analysis create:

```text
LaunchDate
```

from:

```text
LaunchDateTime
```

using:

```powerquery
if [LaunchDateTime] = null
then null
else Date.From([LaunchDateTime])
```

The model should therefore have:

```text
LaunchDateTime → Date/Time
LaunchDate     → Date
```

This preserves the timestamp while providing a clean relationship to `Dim_Date`.

---

# 16. Canonical Created Date

Rename or derive:

```text
CreatedDateTime
```

from:

```text
created_at
```

Use:

```powerquery
try DateTime.From([created_at]) otherwise null
```

If the source already contains a correctly formatted `created_atTime`, use the actual valid date-time field after profiling.

---

# 17. Canonical State Change Date

Create:

```text
StateChangedDateTime
```

from the appropriate source field.

If `state_changed_at` is already Date/Time:

```powerquery
try DateTime.From([state_changed_at]) otherwise null
```

Otherwise use the correctly formatted `state_changed_atTime`.

---

# 18. Do Not Keep the Precomputed Date-Derived Columns in the Final Fact

The dataset contains:

```text
deadlineYM
state_changed_atYM
created_atYM
launched_atYM
deadlineY
state_changed_atY
created_atY
launched_atY
```

These are useful for validating the source, but they are redundant once `Dim_Date` exists.

Your final model should prefer:

```text
Dim_Date[Year]
Dim_Date[YearMonth]
Dim_Date[Month]
Dim_Date[Quarter]
```

rather than storing multiple copies of date attributes in the fact.

Keep the source-derived columns in staging temporarily for QA, then remove them before the final conformed layer unless there is a specific analytical need.

---

# 19. Geography — Country

Rename:

```text
Country
```

to:

```text
CountryName
```

if the values represent country names.

If this column contains codes instead, use:

```text
CountryCode
```

Do not guess which it is from the name alone. Profile the values first.

For example:

```text
US
GB
CA
```

means a code.

While:

```text
United States
United Kingdom
Canada
```

means a name.

---

# 20. Geography — State

Keep:

```text
State
```

as the standardized state/province field.

Clean with:

```powerquery
if [State] = null
then null
else Text.Proper(Text.Trim(Text.Clean(Text.From([State]))))
```

However, **do not rely only on `Text.Proper` for geographic normalization**.

For example:

```text
CA
California
california
```

will still represent multiple business values after simple text formatting.

Create a proper geography mapping table later.

---

# 21. Geography — County

Clean:

```text
County
```

using:

```powerquery
if [County] = null
then null
else Text.Proper(Text.Trim(Text.Clean(Text.From([County]))))
```

Do not append "County" automatically unless you confirm that the source values require it.

---

# 22. Geography — City

Clean:

```text
City
```

with:

```powerquery
if [City] = null
then null
else Text.Trim(Text.Clean(Text.From([City])))
```

Use city as a geographic attribute, not as a unique project identifier.

Multiple Kickstarter projects can obviously belong to the same city.

---

# 23. Latitude and Longitude

Standardize:

```text
Latitude
Longitude
```

to:

```text
Decimal Number
```

Use:

```powerquery
try Number.From([Latitude]) otherwise null
```

and:

```powerquery
try Number.From([Longitude]) otherwise null
```

Then create a QA check for invalid coordinate ranges:

```text
Latitude  < -90 or Latitude > 90
Longitude < -180 or Longitude > 180
```

Do not silently replace invalid coordinates with zero.

---

# 24. Location Grain

The Master dataset gives you enough geographic information to construct:

```text
Country
    ↓
State
    ↓
County
    ↓
City
    ↓
Latitude / Longitude
```

This becomes part of:

```text
Dim_Location
```

later.

Do not create one location key per project.

The same:

```text
New York
California
Los Angeles
```

must be reusable across many campaigns.

---

# 25. Existing `Pledge_per_person`

The source already contains:

```text
Pledge_per_person
```

This corresponds to the business concept:

```text
PledgePerBacker
```

Because we want a consistent canonical name across datasets, create:

```text
PledgePerBacker
```

You have two options:

### Preferred

Recalculate it from the canonical fields:

```powerquery
if [BackerCount] = null
    or [BackerCount] = 0
    or [PledgedUSD] = null
then null
else [PledgedUSD] / [BackerCount]
```

This gives you:

```text
PledgePerBacker
```

Then use the original:

```text
Pledge_per_person
```

only for QA comparison.

For example, create:

```text
PledgePerBacker_Source
```

temporarily and compare the two.

This is much safer than blindly trusting an already-calculated field.

---

# 26. Existing `Prct_goal`

The source contains:

```text
Prct_goal
```

This appears as one of the continuous analytical features used by the original analysis.

Standardize your canonical field as:

```text
GoalAchievementPct
```

Prefer recalculating it from the canonical USD fields:

```powerquery
if [GoalUSD] = null
    or [GoalUSD] = 0
    or [PledgedUSD] = null
then null
else [PledgedUSD] / [GoalUSD]
```

However, this dataset currently provides:

```text
pledgedUSD
```

but your supplied Master schema does not contain a separate USD goal column.

Therefore **do not assume `goal` is already USD-normalized**.

For the Master source specifically:

```text
GoalLocal = goal
PledgedLocal = pledged
PledgedUSD = pledgedUSD
```

but:

```text
GoalUSD
```

must only be created if you can establish a valid conversion rule.

Until then:

```text
GoalUSD = null
```

This prevents mixing local-currency goal values with USD pledged values.

---

# 27. Existing `Length_of_kick`

The source contains:

```text
Length_of_kick
```

which is used in the published analysis as a campaign-duration feature.

Your canonical column should be:

```text
CampaignDurationDays
```

Prefer recalculating it:

```powerquery
if [LaunchDate] = null or [DeadlineDate] = null then
    null
else
    Duration.Days([DeadlineDate] - [LaunchDate])
```

Then compare:

```text
CampaignDurationDays
```

with:

```text
Length_of_kick
```

during QA.

If they disagree materially, investigate rather than silently choosing one.

---

# 28. Pre-Launch Duration

The source contains:

```text
Days_spent_making_campign
```

This is one of the continuous variables used in the published Kickstarter analysis.

Rather than blindly trusting the source calculation, create your own canonical version:

```text
PreLaunchDays
```

using:

```powerquery
if [CreatedDateTime] = null or [LaunchDateTime] = null then
    null
else
    Duration.Days(
        Date.From([LaunchDateTime]) -
        Date.From([CreatedDateTime])
    )
```

Then retain the source field temporarily:

```text
Days_spent_making_campign
```

for QA comparison.

---

# 29. Inception-to-Deadline Duration

The source also contains:

```text
Days_inception_to_Deadline
```

Create the canonical version:

```text
InceptionToDeadlineDays
```

with:

```powerquery
if [CreatedDateTime] = null or [DeadlineDate] = null then
    null
else
    Duration.Days(
        [DeadlineDate] -
        Date.From([CreatedDateTime])
    )
```

Again, retain the source-derived metric temporarily for validation.

---

# 30. Population Metrics

The following fields are **not campaign measures**:

```text
City_Pop
All_Time_Backers_city
Backers_in_city_Y
Backers_in_city_YM
Mean_Pledge_City
Mean_pledge_city_Y
Mean_pledge_city_YM
```

They describe the surrounding geography or an aggregate geographic context.

They should therefore **not be blindly included in `Fact_Campaign`**.

Keep them in `Stg_MasterKickstarter` now and later move them into a geographic fact structure.

---

# 31. City Population

Standardize:

```text
City_Pop
```

to:

```text
CityPopulation
```

Type:

```text
Whole Number
```

This belongs conceptually to the city/location analytical layer.

---

# 32. Backers as Percentage of Population

The source provides:

```text
Backers_as_Prct_of_Pop
Backers_as_Prct_of_Pop_YM
Backers_as_Prct_of_Pop_Y
```

Keep the concepts separate:

```text
BackersPctOfPopulation
BackersPctOfPopulationYM
BackersPctOfPopulationY
```

These are derived population/context metrics, not raw campaign backer counts.

Do not aggregate them with:

```text
SUM()
```

in Power BI.

They are generally candidates for:

```text
AVERAGE
MEDIAN
```

depending on the business question and grain.

---

# 33. City-Level Backer Metrics

Standardize:

```text
Backers_in_city_Y
```

to:

```text
CityBackersYear
```

and:

```text
Backers_in_city_YM
```

to:

```text
CityBackersYearMonth
```

Keep:

```text
All_Time_Backers_city
```

as:

```text
CityAllTimeBackers
```

These should eventually live in:

```text
Fact_CityMetrics
```

rather than being repeated in every campaign row.

The original dataset analysis explicitly uses `All_Time_Backers_city` to visualize city-level Kickstarter backing.

---

# 34. City Pledge Metrics

Rename:

```text
Mean_Pledge_City
```

to:

```text
MeanPledgeCity
```

Rename:

```text
Mean_pledge_city_Y
```

to:

```text
MeanPledgeCityYear
```

Rename:

```text
Mean_pledge_city_YM
```

to:

```text
MeanPledgeCityYearMonth
```

Again:

**do not SUM these fields.**

They are already averages.

---

# 35. `staff_pick`, `spotLight`, `disable_communication`

Normalize:

```text
staff_pick
```

to:

```text
StaffPickFlag
```

Normalize:

```text
spotLight
```

to:

```text
SpotlightFlag
```

Normalize:

```text
disable_communication
```

to:

```text
DisableCommunicationFlag
```

Convert them to logical/Boolean where possible.

If the source contains:

```text
0 / 1
```

then use:

```powerquery
[StaffPickFlag] = 1
```

or equivalent after inspecting the actual source type.

Do not assume that `"True"` and `1` are interchangeable until the values are profiled.

---

# 36. Canonical Campaign Columns

At the end of the campaign normalization phase, you should have:

```text
ProjectID
ProjectName
Blurb
ProjectSlug

Category
Subcategory

CurrencyCode
CurrencySymbol

CountryName
State
County
City
Latitude
Longitude

CreatedDateTime
LaunchDateTime
LaunchDate
DeadlineDate
StateChangedDateTime

GoalLocal
PledgedLocal
PledgedUSD

BackerCount
ProjectStatus

CampaignDurationDays
PreLaunchDays
InceptionToDeadlineDays
PledgePerBacker
GoalAchievementPct

StaffPickFlag
SpotlightFlag
DisableCommunicationFlag

Source_System
Snapshot_Date
```

---

# 37. Source-Specific Columns to Keep Temporarily

For QA and reconciliation, keep these in staging:

```text
Ex_USd

Pledge_per_person
Prct_goal
Length_of_kick

deadlineYM
state_changed_atYM
created_atYM
launched_atYM

deadlineY
state_changed_atY
created_atY
launched_atY

Backers_as_Prct_of_Pop
Backers_as_Prct_of_Pop_YM
Backers_as_Prct_of_Pop_Y

Backers_in_city_Y
Backers_in_city_YM
All_Time_Backers_city

Mean_Pledge_City
Mean_pledge_city_Y
Mean_pledge_city_YM

City_Pop
```

These are valuable, but they do not all belong in your final campaign fact.

---

# 38. Create Source Metadata

Add:

**Custom Column → `Source_System`**

```powerquery
"MasterKickstarter"
```

Then:

**Custom Column → `Snapshot_Date`**

Since this dataset covers historical campaigns from 2009–2017 rather than representing a monthly WebRobots crawl, do not pretend that `Snapshot_Date` is an observation month.

Use a source-publication/snapshot date only if you have established one from your project documentation.

If no defensible snapshot date is available, keep:

```text
Snapshot_Date = null
```

rather than inventing a date.

The campaign dates themselves remain:

```text
CreatedDateTime
LaunchDateTime
DeadlineDate
StateChangedDateTime
```

---

# 39. Suggested Column Data Types

Use the following final staging types:

| Column                   | Data Type      |
| ------------------------ | -------------- |
| ProjectID                | Whole Number   |
| ProjectName              | Text           |
| Blurb                    | Text           |
| ProjectSlug              | Text           |
| Category                 | Text           |
| Subcategory              | Text           |
| CurrencyCode             | Text           |
| CurrencySymbol           | Text           |
| CountryName              | Text           |
| State                    | Text           |
| County                   | Text           |
| City                     | Text           |
| Latitude                 | Decimal Number |
| Longitude                | Decimal Number |
| CreatedDateTime          | Date/Time      |
| LaunchDateTime           | Date/Time      |
| LaunchDate               | Date           |
| DeadlineDate             | Date           |
| StateChangedDateTime     | Date/Time      |
| GoalLocal                | Decimal Number |
| PledgedLocal             | Decimal Number |
| PledgedUSD               | Decimal Number |
| BackerCount              | Whole Number   |
| ProjectStatus            | Text           |
| CampaignDurationDays     | Whole Number   |
| PreLaunchDays            | Whole Number   |
| InceptionToDeadlineDays  | Whole Number   |
| PledgePerBacker          | Decimal Number |
| GoalAchievementPct       | Decimal Number |
| StaffPickFlag            | True/False     |
| SpotlightFlag            | True/False     |
| DisableCommunicationFlag | True/False     |
| Source_System            | Text           |
| Snapshot_Date            | Date           |

---

# 40. Recommended Final Column Order

Use:

```powerquery
Table.ReorderColumns(
    #"Previous Step",
    {
        "ProjectID",
        "ProjectName",
        "Blurb",
        "ProjectSlug",
        "Category",
        "Subcategory",
        "CurrencyCode",
        "CurrencySymbol",
        "CountryName",
        "State",
        "County",
        "City",
        "Latitude",
        "Longitude",
        "CreatedDateTime",
        "LaunchDateTime",
        "LaunchDate",
        "DeadlineDate",
        "StateChangedDateTime",
        "GoalLocal",
        "PledgedLocal",
        "PledgedUSD",
        "BackerCount",
        "ProjectStatus",
        "CampaignDurationDays",
        "PreLaunchDays",
        "InceptionToDeadlineDays",
        "PledgePerBacker",
        "GoalAchievementPct",
        "StaffPickFlag",
        "SpotlightFlag",
        "DisableCommunicationFlag",
        "Source_System",
        "Snapshot_Date"
    }
)
```

This order is designed to make the query easy to inspect and prepare for the conformed layer.

---

# 41. What Happens Next

`Stg_MasterKickstarter` should **not** directly become one giant loaded table.

It will feed several downstream structures.

## Campaign information

```text
Stg_MasterKickstarter
        ↓
Conformed_Project
        ↓
Fact_Campaign
```

## Category

```text
Stg_MasterKickstarter[Category]
        ↓
Dim_Category
```

## Geography

```text
Country
State
County
City
Latitude
Longitude
        ↓
Dim_Location
```

## City metrics

```text
CityPopulation
CityAllTimeBackers
CityBackersYear
CityBackersYearMonth
MeanPledgeCity
MeanPledgeCityYear
MeanPledgeCityYearMonth
        ↓
Fact_CityMetrics
```

This is the key reason we are doing this staging phase carefully.

The Master dataset is both **campaign-level** and **geographic-enrichment** data. The original analysis itself uses city-level and state-level aggregations separately, which supports treating those attributes as a distinct analytical layer rather than repeating them as ordinary campaign measures.

---

# 42. Important Rule for This Dataset

Do **not** take these:

```text
CityPopulation
CityAllTimeBackers
MeanPledgeCity
MeanPledgeCityYear
MeanPledgeCityYearMonth
```

and put them into your final:

```text
Fact_Campaign
```

as if every row were an independent city observation.

That would cause a classic grain problem.

Example:

```text
Los Angeles
100 campaigns
CityPopulation = 4,000,000
```

If population is stored on all 100 campaign rows, a naive:

```DAX
SUM(Fact_Campaign[CityPopulation])
```

would produce:

```text
400,000,000
```

instead of:

```text
4,000,000
```

That is why these values belong in the appropriate geographic grain.

---

# 43. `Stg_MasterKickstarter` Final Responsibility

The final responsibility of this query is:

```text
RAW MASTER CSV
      ↓
Clean
      ↓
Standardize
      ↓
Type
      ↓
Normalize
      ↓
Create canonical campaign fields
      ↓
Preserve geographic enrichment
      ↓
Validate source-derived metrics
      ↓
Attach source lineage
      ↓
DO NOT LOAD
```

The next layer will decide which columns become:

```text
Dim_Project
Dim_Category
Dim_Location
Dim_Currency
Dim_Status
Dim_Date

Fact_Campaign
Fact_CityMetrics
```

rather than loading the entire 57-column Master dataset into Power BI's semantic model.
