# Publishing to GitHub: Software Engineering Best Practices

As a Data/Analytics Engineer, your GitHub repository is your portfolio. Publishing a project isn't just about uploading files; it's about showcasing version control discipline, proper environment isolation, and clean repository management. 

Follow these steps to safely push your local project to GitHub.

---

## Phase 1: The Pre-Flight Check (Crucial)

Before initializing Git, we must guarantee that your gigabytes of raw and extracted data do not get pushed. GitHub has a strict 100MB file limit, and pushing data violates SWE best practices (data belongs in databases or data lakes, code belongs in Git).

1. **Verify your `.gitignore`:** Ensure the `.gitignore` file we created earlier is sitting at the very root of your project folder (next to your `README.md`).
2. **Confirm Data Exclusion:** Open the `.gitignore` and ensure `data/`, `*.csv`, `*.json`, and `*.pbix` (optional, as PBIX are large binary files) are listed.

---

## Phase 2: Local Version Control (Git Init)

Open your terminal (or the integrated terminal in VS Code/Antigravity IDE) and ensure you are in the root directory of your project (`D:\courses\Data Analysis 26-27\Projects\Kickstarter Projects`).

1. **Initialize the local repository:**
   ```bash
   git init
   ```
2. **Check the status:** This command will show you what files Git sees. You should see `src/`, `docs/`, `scripts/`, `README.md`, etc., but you **should NOT** see your `data/` folder listed.
   ```bash
   git status
   ```
3. **Stage all safe files:**
   ```bash
   git add .
   ```
4. **Make your first commit:** Use a clear, imperative commit message.
   ```bash
   git commit -m "Initial commit: Add ETL scripts, project documentation, and metadata generator"
   ```

---

## Phase 3: Creating the Remote Repository

1. Go to [GitHub.com](https://github.com/) and log in.
2. Click the **"+"** icon in the top right corner and select **New repository**.
3. **Repository name:** Use one of our previous ideas (e.g., `kickstarter-analytics-engineering`).
4. **Description:** "End-to-end data pipeline and Power BI model for Kickstarter campaign analysis."
5. **Visibility:** Public (so recruiters and peers can see it).
6. **CRITICAL:** Do **NOT** check "Add a README file" or "Add .gitignore". You already have these locally. If you check these, it will create conflicts.
7. Click **Create repository**.

---

## Phase 4: Linking and Pushing

GitHub will now show you a screen with setup instructions. Look for the section titled **"…or push an existing repository from the command line"**.

Copy and paste those three commands into your terminal one by one. They will look exactly like this:

1. **Link your local repo to GitHub:**
   ```bash
   git remote add origin https://github.com/YOUR-USERNAME/kickstarter-analytics-engineering.git
   ```
2. **Ensure your main branch is named 'main'** (modern naming convention):
   ```bash
   git branch -M main
   ```
3. **Push your code to the remote repository:**
   ```bash
   git push -u origin main
   ```

---

## Phase 5: SWE Best Practices for Ongoing Work

Now that your project is live, treat it like a professional software project.

* **Never push directly to `main` again.** When you want to add a new Python script or update a Power BI concept, create a branch first:
  ```bash
  git checkout -b feature/add-new-dax-measures
  ```
* **Commit frequently:** Make small, logical commits (e.g., `git commit -m "Update deduplication M-code in playbook"`).
* **Merge via Pull Requests (PRs):** Push your branch to GitHub (`git push origin feature/add-new-dax-measures`), go to GitHub, and open a Pull Request. Review your own code before merging it into `main`.
* **Track Power BI correctly:** Since `.pbix` files are binaries, Git can't track line-by-line changes. As a Senior BI Developer, consider saving your Power BI file using the new **Power BI Project (`.pbip`)** format. This saves the metadata and model as plain text files, making it incredibly Git-friendly!