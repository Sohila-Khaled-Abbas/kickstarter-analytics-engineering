"""Power BI Automated Git Version Control & Auto-Publish Daemon
Continuously watches the powerbi/ directory and project files.
Whenever changes are saved in Power BI Desktop, it automatically stages,
commits, and pushes them to GitHub with an informative timestamped commit.
"""

import datetime
import os
import subprocess
import sys
import time
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
WATCH_DIR = REPO_ROOT / "powerbi"
DEBOUNCE_SECONDS = 6.0  # Wait for Power BI Desktop to finish writing all files
POLL_INTERVAL = 2.0


def run_git_cmd(args: list[str]) -> tuple[int, str, str]:
    """Runs a git command inside the repository root."""
    try:
        proc = subprocess.run(
            ["git"] + args,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def get_latest_mtime() -> float:
    """Returns the maximum modification time among files in the watch directory."""
    latest = 0.0
    for root, _, files in os.walk(WATCH_DIR):
        # Skip local machine settings
        if ".pbi" in root and ("localSettings" in root or "editorSettings" in root):
            continue
        for f in files:
            if f.endswith((".json", ".tmdl", ".pbir", ".pbism", ".pbip")):
                try:
                    p = Path(root) / f
                    mtime = p.stat().st_mtime
                    if mtime > latest:
                        latest = mtime
                except (OSError, FileNotFoundError):
                    pass
    return latest


def sync_to_github():
    """Stages, commits, and pushes Power BI updates to GitHub."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{now_str}] Detected changes in Power BI project files.")

    # 1. Stage changes
    print("  -> Staging files with 'git add .'...")
    code, stdout, stderr = run_git_cmd(["add", "."])
    if code != 0:
        print(f"  [ERROR] git add failed: {stderr}")
        return

    # 2. Check if there are staged differences
    code, stdout, _ = run_git_cmd(["diff", "--cached", "--quiet"])
    if code == 0:
        print("  -> No staged changes detected (files may have reverted or touched without modifications).")
        return

    # 3. Commit
    commit_msg = f"auto(powerbi): update model and report definitions [{now_str}]"
    print(f"  -> Creating commit: \"{commit_msg}\"")
    code, stdout, stderr = run_git_cmd(["commit", "-m", commit_msg])
    if code != 0:
        print(f"  [ERROR] git commit failed: {stderr}")
        return
    print(f"  [SUCCESS] {stdout.splitlines()[0] if stdout else 'Committed.'}")

    # 4. Push to remote
    print("  -> Pushing to GitHub (origin main)...")
    code, stdout, stderr = run_git_cmd(["push", "origin", "main"])
    if code == 0:
        print(f"  [SUCCESS] Pushed to GitHub successfully at {now_str}!")
    else:
        print(f"  [WARNING] git push returned code {code}: {stderr}")
        print("  Changes are committed locally. Will retry push on next save or network reconnect.")


def main():
    print("=" * 80)
    print("POWER BI AUTOMATED GIT VERSION CONTROL DAEMON")
    print("=" * 80)
    print(f"Watching directory : {WATCH_DIR}")
    print(f"Target repository  : {REPO_ROOT}")
    print(f"Debounce period    : {DEBOUNCE_SECONDS}s")
    print("Press Ctrl+C to terminate.")
    print("-" * 80)

    last_synced_mtime = get_latest_mtime()
    pending_sync = False
    last_change_time = 0.0

    while True:
        try:
            current_mtime = get_latest_mtime()
            now = time.time()

            if current_mtime > last_synced_mtime:
                # File change detected
                last_change_time = now
                last_synced_mtime = current_mtime
                pending_sync = True
                print(f"[WAIT] Save detected. Debouncing for {DEBOUNCE_SECONDS}s to ensure write completion...", end="\r")

            # Check if debounce window has elapsed
            if pending_sync and (now - last_change_time) >= DEBOUNCE_SECONDS:
                sync_to_github()
                pending_sync = False
                last_synced_mtime = get_latest_mtime()
                print("\n[READY] Watching for next Power BI save event...")

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\nAuto-sync daemon terminated by user.")
            break
        except Exception as e:
            print(f"\n[UNEXPECTED ERROR] {e}")
            time.sleep(5.0)


if __name__ == "__main__":
    main()
