## Summary of Changes
<!-- Provide a clear, concise summary of the changes introduced in this PR. -->

### Type of Change
- [ ] 🌟 New Feature (new DAX measure, dimension, or fact table)
- [ ] 🐛 Bug Fix (modeling relationship, query transformation, or data type correction)
- [ ] ⚡ Performance Optimization (VertiPaq compression, M query folding, or DAX refactoring)
- [ ] 📚 Documentation Update (playbook, data dictionary, or architecture guides)
- [ ] 🔧 Engineering Tooling (Python scraper, profiler, CI/CD workflow)

---

## Analytics Engineering Verification Checklist

### Power Query M Layer
- [ ] Intermediate staging/conformed queries have **Enable Load = False**.
- [ ] Queries are placed in the correct numbered group (`00_Parameters` through `99_QA`).
- [ ] Data types are explicitly cast for all modified columns.
- [ ] Character encoding is properly declared (`1252` for Kaggle 2016, `65001` for UTF-8).

### Data Model & TMDL Layer
- [ ] All relationships are **One-to-Many (1:*)** with **Single** cross-filter direction.
- [ ] Foreign keys join strictly on integer surrogate keys (`*Key`).
- [ ] All foreign key columns in Fact tables are hidden in Report View.
- [ ] Inactive relationships (e.g. `DeadlineDateKey`) are tested using `USERELATIONSHIP()`.

### DAX Measures
- [ ] Measures are centralized in the `_Measures` table and placed in a display folder.
- [ ] All divisions use `DIVIDE()` with safe zero or blank fallbacks.
- [ ] Measures have explicit formatting strings applied (`Currency`, `Percentage`, or `Integer`).

### Data Quality & Auditing
- [ ] All assertion queries in `99_QA` return exactly **0 rows**.
- [ ] No raw data files (`.csv`, `.json`, `.parquet`, `.zip`) are committed in this branch.

---

## Related Issue / Ticket
Closes #
