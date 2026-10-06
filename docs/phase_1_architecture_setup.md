# Phase 1: Architecture & Project Setup

**Objective:** Establish a robust architectural foundation using a Galaxy Schema (Fact Constellation) and configure the Power Query workspace for enterprise-grade ETL.

## 1. The Galaxy Schema (Fact Constellation)
A standard Star Schema typically revolves around a single Fact table. However, our Kickstarter data contains distinct concepts that exist at entirely different levels of granularity (e.g., static campaign details vs. monthly recurring snapshots vs. city-level demographics).

To prevent data duplication and many-to-many relationship errors, we utilize a **Galaxy Schema**. This architecture features multiple Fact tables that share common, conformed Dimensions.

### The Golden Rule of Grain
Before importing any data, we define the exact grain (the meaning of a single row) for every Fact table. **Never mix these grains.**

| Table Name | Grain Definition | Data Source |
| :--- | :--- | :--- |
| `Fact_Campaign` | One row per unique Kickstarter project. | Kaggle (2018/2016) + Master |
| `Fact_CampaignSnapshot` | One row per project *per WebRobots snapshot date*. | WebRobots JSON/CSV |
| `Fact_CityMetrics` | One row per city per defined period/source. | MasterKickstarter |
| `Fact_StateMetrics` | One row per state per defined period/source. | Mapping.csv |
| `Fact_CountyMetrics` | One row per county per defined period/source. | County.csv |

## 2. Power Query Workspace Organization
To maintain a clean and logical ETL dependency chain, strictly organize your Power Query Editor using the following 7-tier Grouping structure. (Right-click the queries pane -> *New Group*).

```text
00 Parameters
 ├── pDataFolder
 ├── pWebRobotsFolder
 └── pDefaultCurrency

01 Sources (Raw connection only, no transformations)
 ├── Src_Kaggle_2016
 ├── Src_Kaggle_2018
 ├── Src_MasterKickstarter
 ├── Src_WebRobots
 ├── Src_Mapping
 └── Src_County

02 Staging (Cleaning, encoding, type casting, JSON parsing)
 ├── Stg_Kaggle_2016
 ├── Stg_Kaggle_2018
 └── ...

03 Conformed (Appending & Deduplication for Dimensions)
 ├── Conformed_Project
 ├── Conformed_Category
 └── ...

04 Dimensions (Enable Load)
 ├── Dim_Project
 ├── Dim_Date
 └── ...

05 Facts (Enable Load)
 ├── Fact_Campaign
 ├── Fact_CampaignSnapshot
 └── ...

99 QA (Audits & Assertions)
 ├── QA_DuplicateProjects
 ├── QA_OrphanLocations
 └── QA_NullKeys
```

*Note: Only queries inside the `04 Dimensions` and `05 Facts` folders should have **"Enable Load"** checked. Everything else should be disabled to optimize RAM.*

## 3. Parameterization
In the `00 Parameters` folder, create a new parameter:
*   **Name:** `pDataFolder`
*   **Type:** Text
*   **Current Value:** `D:\courses\Data Analysis 26-27\Projects\Kickstarter Projects\data\raw\`

Use this parameter in all your `01 Sources` connections so the project can be easily migrated to another machine or cloud environment.