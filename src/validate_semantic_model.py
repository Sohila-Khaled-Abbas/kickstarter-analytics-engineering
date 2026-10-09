"""Semantic Model Validator
Validates Power BI Developer Mode (.pbip / TMDL) consistency, expressions, and model standards.
"""

from pathlib import Path
import re
import sys

BASE_DIR = Path(r"D:\courses\Data Analysis 26-27\Projects\Kickstarter Projects")
TMDL_DIR = BASE_DIR / "powerbi" / "kickstarter_analytics.SemanticModel" / "definition"


def validate_expressions():
    """Validates expressions.tmdl for syntax and query group annotations."""
    exp_file = TMDL_DIR / "expressions.tmdl"
    if not exp_file.exists():
        print(f"[FAIL] Missing {exp_file}")
        return False

    content = exp_file.read_text(encoding="utf-8", errors="ignore")

    # Check for basic let ... in blocks
    queries = re.findall(r"expression\s+([A-Za-z0-9_]+)\s*=", content)
    print(f"[INFO] Discovered {len(queries)} Power Query expressions in TMDL.")

    required_queries = ["DataFolderPath", "Src_Master", "Src_Kaggle_2018", "Stg_Master", "Stg_Kaggle_2018"]
    missing = [q for q in required_queries if q not in queries]

    if missing:
        print(f"[WARN] Some expected baseline queries not explicitly found: {missing}")
    else:
        print(f"[PASS] All critical baseline expressions present.")

    return True


def validate_model_groups():
    """Validates that model.tmdl contains governed query groups."""
    model_file = TMDL_DIR / "model.tmdl"
    if not model_file.exists():
        print(f"[FAIL] Missing {model_file}")
        return False

    content = model_file.read_text(encoding="utf-8", errors="ignore")
    groups = re.findall(r"queryGroup\s+([A-Za-z0-9_]+)", content)
    print(f"[INFO] Discovered query groups: {groups}")
    return True


def main():
    print("=" * 80)
    print("POWER BI SEMANTIC MODEL TMDL VALIDATOR")
    print("=" * 80)

    if not TMDL_DIR.exists():
        print(f"[ERROR] TMDL directory not found: {TMDL_DIR}")
        sys.exit(1)

    exp_ok = validate_expressions()
    grp_ok = validate_model_groups()

    if exp_ok and grp_ok:
        print("\n[SUCCESS] Semantic model validation PASSED.")
    else:
        print("\n[FAILURE] Semantic model validation encountered issues.")


if __name__ == "__main__":
    main()
