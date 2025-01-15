import subprocess
import csv
import datetime
import os
import logging

# Set up logging
logging.basicConfig(
    filename="debug.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Define default period (1 month ago from today)
default_period = datetime.datetime.now() - datetime.timedelta(days=30)

# Function to get the git log with file changes (added, removed, modified)
def get_git_log(since_date):
    try:
        logging.info(f"Fetching git log since {since_date}")
        git_log_command = [
            "git", "log", "--since", since_date, "--pretty=format:'%H,%ad,%s'", "--numstat"
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

# Function to safely convert values to integers, handling cases where values are not numbers
def safe_int(value):
    try:
        return int(value)
    except ValueError:
        return 0

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
        commit_data.append(commit_info)
    
    logging.info(f"Parsed {len(commit_data)} commits.")
    return commit_data

# Function to save commit data to CSV
def save_to_csv(commit_data, file_name="commit_churn.csv"):
    try:
        header = ["commit_id", "date", "message", "added_lines", "removed_lines"]
        logging.info(f"Saving commit data to {file_name}")

        with open(file_name, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(header)
            
            for commit in commit_data:
                writer.writerow([
                    commit["commit_id"],
                    commit["date"],
                    commit["message"],
                    commit["added_lines"],
                    commit["removed_lines"]
                ])
        
        logging.info(f"Data successfully saved to {file_name}")
    except Exception as e:
        logging.error(f"Error saving data to CSV: {str(e)}")
        raise

# Main function to execute the script
def main():
    try:
        # Get the period (default to 1 month ago)
        since_date = default_period.strftime("%Y-%m-%d")
        logging.info(f"Using default period: {since_date}")
        
        # Get the git log output
        git_log_output = get_git_log(since_date)
        
        # Parse the git log output
        commit_data = parse_git_log(git_log_output)
        
        # Save the parsed data to CSV
        save_to_csv(commit_data)
    except Exception as e:
        logging.error(f"Script failed: {str(e)}")

# Run the script
if __name__ == "__main__":
    main()
