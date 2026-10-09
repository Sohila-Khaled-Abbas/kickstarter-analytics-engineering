# Contributing to Kickstarter Analytics Engineering

First off, thank you for considering contributing to the **Kickstarter Analytics Engineering Platform**! 

This repository treats Power BI as a software-engineered analytical platform. We maintain rigorous standards for code quality, architectural consistency, and tabular modeling discipline.

---

## 1. Code of Conduct & Core Principles

1. **Analytics Engineering First**: Never load raw, dirty data directly into visual models. All data flows through Bronze → Silver → Gold.
2. **Explicit Typings**: Every column must have an explicit data type in Power Query M.
3. **Safe DAX**: Always use `DIVIDE()` for divisions and `KEEPFILTERS()` for non-destructive filtering.
4. **No Opaque Binaries**: Never commit `.pbix` binary files. All modifications must be made within the `.pbip` developer mode structure.

---

## 2. Development Workflow

### A. Local Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/Sohila-Khaled-Abbas/kickstarter-analytics-engineering.git
   cd kickstarter-analytics-engineering
   ```
2. Set up Python environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Open `powerbi/kickstarter_analytics.pbip` in Power BI Desktop (requires PBIP Preview enabled).
4. Verify the `DataFolderPath` parameter points to your local `data/` folder.

---

### B. Git Branching & Commits
We follow **Conventional Commits**:

- `feat(dax)`: Add new DAX measure or KPI folder
- `feat(pq)`: Add or optimize Power Query M staging/conformed query
- `fix(model)`: Correct relationship cardinality or cross-filter direction
- `docs(guide)`: Update documentation or playbook guides
- `refactor(tmdl)`: Reorganize display folders or TMDL syntax
- `test(qa)`: Add new assertion test query in `99_QA`

#### Example:
```bash
git checkout -b feat/add-velocity-measures
# Make changes in Power BI Desktop or Tabular Editor
git commit -m "feat(dax): add rolling 12M pledged USD and duration velocity measures"
git push origin feat/add-velocity-measures
```

---

## 3. Pull Request (PR) Checklist

Before submitting a Pull Request, verify:

- [ ] All new queries have been placed in their appropriate numbered group (`00_Parameters` to `99_QA`).
- [ ] Intermediate queries in `01_Sources`, `02_Staging`, `03_Conformed`, and `99_QA` have **Enable Load = False**.
- [ ] Fact-to-Dimension relationships join strictly on integer surrogate keys (`*Key`).
- [ ] No bi-directional (`Both`) cross-filtering has been introduced.
- [ ] All foreign key columns in Fact tables are set to **Hidden in Report View**.
- [ ] All assertion queries in `99_QA` return zero rows.
- [ ] `git status` confirms that no raw `.csv`, `.json`, or temporary `.pbicache` files are staged.
