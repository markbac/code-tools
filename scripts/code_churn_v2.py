import subprocess
import csv
import datetime
import logging
import argparse
import os

# Function to get the current active branch
def get_current_branch():
    try:
        # Get the current active branch
        current_branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).strip().decode('utf-8')
        return current_branch
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get current branch: {e}")
        return None

# Function to safely convert values to integers, handling cases where values are not numbers
def safe_int(value):
    try:
        return int(value)
    except ValueError:
        return 0

# Function to get the actual number of modified lines, considering merge commits
def get_modified_lines(commit_id):
    try:
        # Check if the commit is a merge commit by using git show
        merge_check_command = ["git", "show", "--no-patch", "--pretty=%P", commit_id]
        result = subprocess.run(merge_check_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result.returncode != 0:
            logging.error(f"Error checking commit for merge status: {result.stderr.decode('utf-8')}")
            return 0

        parent_commits = result.stdout.decode('utf-8').strip()
        # If there are two parent commits, it's a merge commit
        if len(parent_commits.split()) == 2:
            # Merge commit, diff with both parents
            diff_command = ["git", "diff", "--numstat", f"{commit_id}^1..{commit_id}^2"]
        else:
            # Not a merge commit, diff with the single parent
            diff_command = ["git", "diff", "--numstat", f"{commit_id}^"]

        # Run the diff command
        result = subprocess.run(diff_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result.returncode != 0:
            logging.error(f"Error running diff command for commit {commit_id}: {result.stderr.decode('utf-8')}")
            return 0
        
        diff_output = result.stdout.decode('utf-8')
        modified_lines = 0
        
        # Process each file change in the diff output
        for line in diff_output.splitlines():
            parts = line.split("\t")
            if len(parts) == 3:
                added, removed, _ = parts
                # Actual modifications are added + removed lines
                modified_lines += safe_int(added) + safe_int(removed)
        
        logging.debug(f"Modified lines in commit {commit_id}: {modified_lines}")
        return modified_lines
    except Exception as e:
        logging.error(f"Error getting modified lines for commit {commit_id}: {str(e)}")
        return 0

# Function to fetch the git log based on the provided start and end dates and branch
def get_git_log(branch, start_date, end_date):
    try:
        logging.info(f"Fetching git log for branch {branch} from {start_date} to {end_date}")
        git_log_command = [
            "git", "log", f"{branch}", "--since", start_date, "--until", end_date,
            "--pretty=format:'%H,%ad,%s'", "--numstat"
        ]
        
        result = subprocess.run(git_log_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result.returncode != 0:
            logging.error(f"Error running git command: {result.stderr.decode('utf-8')}")
            raise Exception(f"Error running git command: {result.stderr.decode('utf-8')}")
        
        logging.info(f"Successfully fetched git log.")
        return result.stdout.decode('utf-8')
    except Exception as e:
        logging.error(f"Failed to fetch git log: {str(e)}")
        raise

# Function to parse the git log output
def parse_git_log(git_log_output):
    commit_data = []
    commit_lines = git_log_output.splitlines()
    
    commit_info = {}
    total_added = 0
    total_removed = 0
    
    for line in commit_lines:
        # Check for commit header
        if line.startswith("'"):
            # If there's previous commit data, store it
            if commit_info:
                commit_info['added_lines'] = total_added
                commit_info['removed_lines'] = total_removed
                commit_info['modified_lines'] = get_modified_lines(commit_info['commit_id'])  # Get actual modified lines
                commit_data.append(commit_info)
                logging.debug(f"Stored commit: {commit_info}")

            # Parse commit header (commit ID, date, message)
            parts = line.strip("'").split(",", 3)
            commit_info = {
                "commit_id": parts[0],
                "date": parts[1],  # Extracted date properly now
                "message": parts[2]
            }
            total_added = 0
            total_removed = 0
            logging.debug(f"Parsed commit header: {commit_info}")
        
        # Process file change stats
        else:
            parts = line.split("\t")
            if len(parts) == 3:  # Only process if the line is well-formed
                added = safe_int(parts[0])
                removed = safe_int(parts[1])
                file_name = parts[2]
                total_added += added
                total_removed += removed
                logging.debug(f"File changed: {added} added, {removed} removed, {file_name}")
            else:
                logging.warning(f"Skipping malformed line: {line}")
    
    # Add the last commit data
    if commit_info:
        commit_info['added_lines'] = total_added
        commit_info['removed_lines'] = total_removed
        commit_info['modified_lines'] = get_modified_lines(commit_info['commit_id'])  # Get actual modified lines
        commit_data.append(commit_info)
    
    logging.info(f"Parsed {len(commit_data)} commits.")
    return commit_data

# Function to save commit data to CSV
def save_to_csv(commit_data, file_name="commit_churn.csv"):
    try:
        header = ["commit_id", "date", "message", "added_lines", "removed_lines", "modified_lines"]
        logging.info(f"Saving commit data to {file_name}")

        # Sort commit data by date (oldest first)
        commit_data.sort(key=lambda x: x["date"])
        
        with open(file_name, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(header)
            
            for commit in commit_data:
                writer.writerow([
                    commit["commit_id"],
                    commit["date"],
                    commit["message"],
                    commit["added_lines"],
                    commit["removed_lines"],
                    commit["modified_lines"]
                ])
        
        logging.info(f"Data successfully saved to {file_name}")
    except Exception as e:
        logging.error(f"Error saving data to CSV: {str(e)}")
        raise

# Argument Parsing
def parse_arguments():
    parser = argparse.ArgumentParser(description="Calculate code churn in a Git repository.")
    parser.add_argument('--branch', type=str, default=get_current_branch(), help="Git branch to analyze (default: current active branch)")
    parser.add_argument('--start-date', type=str, default=(datetime.datetime.now() - datetime.timedelta(days=180)).strftime('%Y-%m-%d'), 
                        help="Start date (default: 6 months ago)")
    parser.add_argument('--end-date', type=str, default=datetime.datetime.now().strftime('%Y-%m-%d'), 
                        help="End date (default: now)")
    parser.add_argument('--log-file', type=str, default=None, help="Log file name (default: off)")
    parser.add_argument('--log-level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
                        help="Logging level (default: INFO)")
    
    return parser.parse_args()

# Setup logging
def setup_logging(log_file=None, log_level='INFO'):
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(level=numeric_level)
    
    if log_file:
        # If log file is specified, log to file as well
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)
        logging.getLogger().setLevel(logging.INFO)  # turn off terminal logging

# Main function to execute the script
def main():
    args = parse_arguments()
    
    # Set up logging
    log_file = args.log_file if args.log_file else None
    setup_logging(log_file=log_file, log_level=args.log_level)

    try:
        # Fetch the git log for the given parameters
        git_log_output = get_git_log(args.branch, args.start_date, args.end_date)
        
        # Parse the git log output
        commit_data = parse_git_log(git_log_output)
        
        # Save the parsed data to CSV
        save_to_csv(commit_data, f"{args.branch}_{args.start_date}_{args.end_date}_commit_churn.csv")
    except Exception as e:
        logging.error(f"Script failed: {str(e)}")

if __name__ == "__main__":
    main()
