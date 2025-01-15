import subprocess
import argparse
import logging
from datetime import datetime, timedelta
import csv

def configure_logging(log_level, log_file):
    """Configure logging based on user preferences."""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    if log_file:
        logging.basicConfig(filename=log_file, level=log_level, format=log_format)
    else:
        logging.basicConfig(level=log_level, format=log_format)

def run_git_command(command):
    """Run a Git command and return the output."""
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        logging.debug(f"Command: {' '.join(command)}\nOutput: {result.stdout.strip()}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running command: {' '.join(command)}\n{e.stderr}")
        return None

def detect_default_branch():
    """Detect the default branch of the repository."""
    default_branch = run_git_command(["git", "symbolic-ref", "refs/remotes/origin/HEAD"])
    if default_branch:
        default_branch_name = default_branch.split("/")[-1]
        logging.debug(f"Default branch detected: {default_branch_name}")
        return default_branch_name
    logging.error("Failed to detect the default branch.")
    return None

def get_all_branches():
    """Get a list of all branches in the repository."""
    logging.debug("Fetching all branches.")
    branches = run_git_command(["git", "branch", "--all", "--no-color"])
    if branches:
        branch_list = [branch.strip("* ").strip() for branch in branches.splitlines()]
        logging.debug(f"Branches retrieved: {branch_list}")
        return branch_list
    logging.warning("No branches found or unable to fetch branches.")
    return []

def get_branch_creation_date(branch, default_branch):
    """Get the creation date of a branch."""
    logging.debug(f"Fetching creation date for branch: {branch}")
    # Find the first commit unique to this branch compared to the default branch
    first_unique_commit = run_git_command(["git", "rev-list", "--boundary", branch, f"^{default_branch}", "--reverse", "--max-parents=1"])
    if first_unique_commit:
        first_commit_hash = first_unique_commit.splitlines()[0].lstrip('-')  # Strip the boundary marker
        commit_date = run_git_command(["git", "show", "-s", "--format=%ci", first_commit_hash])
        if commit_date:
            logging.debug(f"Branch {branch} creation date: {commit_date}")
            return datetime.strptime(commit_date, "%Y-%m-%d %H:%M:%S %z")
        logging.warning(f"No valid commit date found for branch: {branch}")
    else:
        logging.warning(f"No unique commits found for branch: {branch}")
    return None

def get_branch_parent(branch, default_branch):
    """Find the parent branch where the given branch was created."""
    logging.debug(f"Fetching parent branch for: {branch}")
    merge_base = run_git_command(["git", "merge-base", default_branch, branch])
    if merge_base:
        parent = run_git_command(["git", "name-rev", "--name-only", merge_base])
        logging.debug(f"Parent branch for {branch}: {parent}")
        return parent
    logging.warning(f"Unable to determine parent branch for: {branch}")
    return None

def has_branch_merged(branch):
    """Check if the branch has been merged back to its parent."""
    logging.debug(f"Checking if branch {branch} has been merged.")
    merged_branches = run_git_command(["git", "branch", "--merged"])
    if merged_branches and branch in merged_branches:
        logging.debug(f"Branch {branch} has been merged.")
        return True
    logging.debug(f"Branch {branch} has not been merged.")
    return False

def main():
    parser = argparse.ArgumentParser(description="Analyse Git branches.")
    parser.add_argument("--start-date", type=lambda d: datetime.strptime(d, "%Y-%m-%d"),
                        default=(datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d"),
                        help="Start date for branch analysis (YYYY-MM-DD). Default: 6 months ago.")
    parser.add_argument("--end-date", type=lambda d: datetime.strptime(d, "%Y-%m-%d"),
                        default=datetime.now().strftime("%Y-%m-%d"),
                        help="End date for branch analysis (YYYY-MM-DD). Default: now.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Logging level. Default: INFO.")
    parser.add_argument("--log-file", help="Log file to write logs. If specified, terminal logging is disabled.")
    parser.add_argument("--output", help="CSV file to save branch analysis. Default: repo_name_startdate_enddate.csv")

    args = parser.parse_args()
    configure_logging(args.log_level, args.log_file)

    start_date = args.start_date
    end_date = args.end_date

    logging.info(f"Starting branch analysis for date range: {start_date} to {end_date}")

    default_branch = detect_default_branch()
    if not default_branch:
        logging.error("Default branch detection failed. Exiting.")
        return

    branches = get_all_branches()
    if not branches:
        logging.warning("No branches found or unable to fetch branches.")
        return

    logging.debug(f"Branches found: {branches}")

    repo_name = run_git_command(["git", "rev-parse", "--show-toplevel"])
    if repo_name:
        repo_name = repo_name.split('/')[-1]
    else:
        logging.error("Failed to determine repository name.")
        return

    output_file = args.output or f"{repo_name}_{start_date.date()}_{end_date.date()}.csv"

    data = []

    for branch in branches:
        logging.debug(f"Analysing branch: {branch}")
        if "remotes/" in branch:  # Skip remote branches for simplicity
            logging.debug(f"Skipping remote branch: {branch}")
            continue

        created_date = get_branch_creation_date(branch, default_branch)
        if created_date:
            created_date_naive = created_date.replace(tzinfo=None)  # Make offset-naive for comparison
            if not (start_date <= created_date_naive <= end_date):
                logging.debug(f"Branch {branch} creation date {created_date_naive} is outside date range.")
                continue

        parent_branch = get_branch_parent(branch, default_branch)
        merged = has_branch_merged(branch)

        if created_date:
            age_days = (datetime.now() - created_date.replace(tzinfo=None)).days
            created_str = created_date.strftime("%Y-%m-%d %H:%M:%S")
        else:
            age_days = "N/A"
            created_str = "N/A"

        logging.debug(f"Branch: {branch}, Parent: {parent_branch}, Created: {created_str}, Age: {age_days}, Merged: {merged}")
        data.append([branch, parent_branch or 'Unknown', created_str, age_days, str(merged)])

    if data:
        logging.info(f"Saving analysis to {output_file}")
        with open(output_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Branch", "Parent", "Created (UTC)", "Age (days)", "Merged"])
            writer.writerows(data)
    else:
        logging.warning("No branches match the specified date range.")

if __name__ == "__main__":
    main()
