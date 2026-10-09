# Changelog

All notable changes to the **Kickstarter Analytics Engineering Platform** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-10-09

### Added
- **Medallion Architecture Pipeline**: Implemented 3-tier Bronze → Silver → Gold transformation architecture in Power Query M.
- **Galaxy Constellation Schema**: Created multi-fact constellation schema separating granular project records (`Fact_Campaign`), recurring time-series crawls (`Fact_CampaignSnapshot`), and geographic benchmarks (`Fact_CityMetrics`, `Dim_State_Metrics`, `Dim_County_Metrics`).
- **Conformed Dimensions**: Engineered conformed dimension suite (`Dim_Project`, `Dim_Category`, `Dim_Location`, `Dim_Currency`, `Dim_Status`, `Dim_Date`).
- **Deterministic Deduplication Engine**: Built multi-source recency and state-precedence deduplication hierarchy in Power Query M utilizing memory buffering (`Table.Buffer`).
- **Centralized DAX Semantic Layer**: Designed enterprise `_Measures` table housing 30+ governed KPIs across 7 display folders.
- **Data Quality Assertion Framework**: Built `99_QA` assertion suite verifying zero duplicate keys, zero orphan foreign keys, non-negative values, and financial reconciliation.
- **Full Step-by-Step Documentation Suite**: Authored 9 exhaustive technical guides (`docs/00_` through `docs/08_`).
- **GitHub Governance Suite**: Added GitHub Actions CI workflows, issue templates, PR template, data dictionary, and architectural decision records.

### Changed
- Migrated legacy fragmented queries into standardized 7-group hierarchy (`00_Parameters` to `99_QA`).
- Standardized character encodings for Kaggle 2016 (`Windows-1252`) and Kaggle 2018 (`UTF-8`).
- Converted UNIX epoch integer timestamps in MasterKickstarter to native DateTime objects.

### Fixed
- Fixed Kaggle 2016 unescaped comma column spillover bug (`Unnamed: 13` through `16`).
- Fixed Cartesian grain explosion caused by denormalizing city population into individual campaign rows.

---

## [1.0.0] - 2024-05-15
- Initial prototype ingestion of MasterKickstarter, Kaggle 2016, and WebRobots data.
- Basic PBIP project initialization.
