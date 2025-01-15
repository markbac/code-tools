import os
import logging
from datetime import datetime
from git import Repo
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
import argparse

# Configure logging
def setup_logging(log_file=None, log_level=logging.WARNING):
    """Set up logging configuration."""
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    
    if log_file:
        logging.basicConfig(level=log_level, format=log_format, filename=log_file, filemode='a')
    else:
        logging.basicConfig(level=log_level, format=log_format)

# Function to calculate lead time and time to resolve issues
def calculate_git_metrics(repo_path):
    """Calculate metrics from Git repository commits."""
    logger = logging.getLogger("calculate_git_metrics")

    try:
        repo = Repo(repo_path)
        if repo.bare:
            logger.error("Invalid Git repository.")
            return []

        logger.info("Calculating Git metrics...")
        metrics = []

        for branch in repo.branches:
            logger.debug(f"Analysing branch: {branch.name}")
            for commit in repo.iter_commits(branch):
                commit_date = datetime.fromtimestamp(commit.committed_date)
                author = commit.author.name
                message = commit.message.strip()

                # Safely check if the commit references an issue (e.g., #1234)
                issue_ref = None
                if "#" in message:
                    parts = message.split("#", 1)
                    if len(parts) > 1 and parts[1].strip():
                        issue_ref = parts[1].split()[0]

                metrics.append({
                    "branch": branch.name,
                    "commit_date": commit_date,
                    "author": author,
                    "message": message,
                    "issue_ref": issue_ref,
                })

        return metrics

    except Exception as e:
        logger.exception("Failed to calculate Git metrics.")
        return []

# Function to fetch PR metrics using Azure DevOps Python SDK
def get_pr_metrics(azure_org_url, azure_project, pat):
    """Fetch Pull Request metrics from Azure DevOps."""
    logger = logging.getLogger("get_pr_metrics")

    try:
        logger.info("Fetching PR metrics from Azure DevOps...")

        # Authenticate and create connection
        credentials = BasicAuthentication("", pat)
        connection = Connection(base_url=azure_org_url, creds=credentials)
        git_client = connection.clients.get_git_client()

        # Fetch pull requests
        prs = git_client.get_pull_requests(azure_project, repository_id=None, status="completed")
        metrics = []

        for pr in prs:
            created_date = pr.creation_date
            completed_date = pr.closed_date
            lead_time = (completed_date - created_date).total_seconds() / 3600 if completed_date else None

            metrics.append({
                "pr_id": pr.pull_request_id,
                "title": pr.title,
                "created_date": created_date,
                "completed_date": completed_date,
                "lead_time_hours": lead_time,
                "reviewers": [reviewer.display_name for reviewer in pr.reviewers],
                "status": pr.status,
            })

        return metrics

    except Exception as e:
        logger.exception("Failed to fetch PR metrics.")
        return []

# Function to test Azure DevOps connectivity using the SDK
def test_azure_connectivity(azure_org_url, azure_project, pat):
    """Test connectivity to Azure DevOps Pull Requests API."""
    logger = logging.getLogger("test_azure_connectivity")

    try:
        logger.info("Testing connection to Azure DevOps Pull Requests API...")

        # Authenticate and create connection
        credentials = BasicAuthentication("", pat)
        connection = Connection(base_url=azure_org_url, creds=credentials)
        git_client = connection.clients.get_git_client()

        # Attempt to fetch pull requests to test connectivity
        prs = git_client.get_pull_requests(azure_project, repository_id=None, status="completed")
        logger.info("Successfully connected to Azure DevOps and fetched pull requests.")

        for pr in prs:
            logger.debug(f"Pull Request: {pr.pull_request_id} - {pr.title}")

        return True

    except Exception as e:
        logger.exception("Failed to connect to Azure DevOps Pull Requests API.")
        return False

# Function to display metrics
def display_metrics(git_metrics, pr_metrics):
    """Display the collected metrics."""
    logger = logging.getLogger("display_metrics")
    
    logger.info("Displaying Git Metrics:")
    for metric in git_metrics:
        logger.info(metric)

    logger.info("\nDisplaying PR Metrics:")
    for metric in pr_metrics:
        logger.info(metric)

# Main script execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metrics Analysis Script")
    parser.add_argument("--repo-path", help="Path to the Git repository", default=".")
    parser.add_argument("--azure-org-url", help="Azure DevOps organisation URL", default="")
    parser.add_argument("--azure-project", help="Azure DevOps project name", default="")
    parser.add_argument("--pat", help="Personal Access Token for Azure DevOps", default="")
    parser.add_argument("--log-file", help="File to write logs to", default=None)
    parser.add_argument("--log-level", help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)", default="WARNING")
    parser.add_argument("--test-connectivity", help="Test connectivity to Azure DevOps", action="store_true")

    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper(), logging.WARNING)
    setup_logging(log_file=args.log_file, log_level=log_level)

    if args.test_connectivity:
        if test_azure_connectivity(args.azure_org_url, args.azure_project, args.pat):
            logging.info("Connectivity test successful.")
        else:
            logging.error("Connectivity test failed.")
        exit()

    logging.info("Starting analysis...")

    # Calculate Git metrics
    git_metrics = calculate_git_metrics(args.repo_path)

    # Fetch PR metrics
    pr_metrics = get_pr_metrics(args.azure_org_url, args.azure_project, args.pat)

    # Display results
    display_metrics(git_metrics, pr_metrics)

    logging.info("Analysis completed.")
