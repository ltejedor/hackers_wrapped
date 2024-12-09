#!/usr/bin/env python3

import requests
from datetime import datetime
from typing import List, Dict, Optional
import os
from dataclasses import dataclass
from datetime import datetime, timezone
import sys
from collections import defaultdict

@dataclass
class GitHubEvent:
    """Represents a GitHub event with essential information."""
    id: str
    type: str
    repo_name: str
    created_at: datetime
    payload: Dict

@dataclass
class GitHubCommit:
    """Represents a GitHub commit with detailed information."""
    sha: str
    author_name: str
    author_email: str
    message: str
    date: datetime
    repo_name: str
    url: str
    stats: Optional[Dict] = None

class GitHubAPI:
    """Class to interact with GitHub API for fetching user events and commits."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the GitHub API client.
        
        Args:
            token: GitHub personal access token (optional but recommended to avoid rate limits)
        """
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "User-Agent": "GitHub-Event-Analyzer",
            "X-GitHub-Api-Version": "2022-11-28"
        })
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def get_user_events_2024(self, username: str) -> List[GitHubEvent]:
        """
        Fetch all events for a user in 2024.
        
        Args:
            username: GitHub username to fetch events for
            
        Returns:
            List of GitHubEvent objects
            
        Raises:
            requests.RequestException: If API request fails
        """
        events = []
        page = 1
        
        while True:
            url = f"{self.BASE_URL}/users/{username}/events"
            params = {
                "page": page,
                "per_page": 100
            }
            
            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                if not data:  # No more events
                    break
                
                for event in data:
                    created_at = datetime.strptime(event["created_at"], "%Y-%m-%dT%H:%M:%SZ")
                    
                    # Only include events from 2024
                    if created_at.year != 2024:
                        continue
                        
                    github_event = GitHubEvent(
                        id=event["id"],
                        type=event["type"],
                        repo_name=event["repo"]["name"],
                        created_at=created_at,
                        payload=event["payload"]
                    )
                    events.append(github_event)
                
                # Check if we should continue pagination
                # GitHub's Events API only returns up to 300 events
                if len(data) < 100 or page * 100 >= 300:
                    break
                    
                page += 1
                
            except requests.RequestException as e:
                print(f"Error fetching events: {e}", file=sys.stderr)
                raise
                
        return events

    def get_commit_details(self, owner: str, repo: str, sha: str) -> Optional[GitHubCommit]:
        """
        Fetch detailed information about a specific commit.
        
        Args:
            owner: Repository owner
            repo: Repository name
            sha: Commit SHA
            
        Returns:
            GitHubCommit object if successful, None otherwise
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits/{sha}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            return GitHubCommit(
                sha=data["sha"],
                author_name=data["commit"]["author"]["name"],
                author_email=data["commit"]["author"]["email"],
                message=data["commit"]["message"],
                date=datetime.strptime(data["commit"]["author"]["date"], "%Y-%m-%dT%H:%M:%SZ"),
                repo_name=f"{owner}/{repo}",
                url=data["html_url"],
                stats=data.get("stats")
            )
        except requests.RequestException as e:
            print(f"Error fetching commit details for {sha}: {e}", file=sys.stderr)
            return None

    def get_user_commits_2024(self, username: str) -> List[GitHubCommit]:
        """
        Fetch all commits made by a user in 2024 using the Events API.
        
        Args:
            username: GitHub username to fetch commits for
            
        Returns:
            List of GitHubCommit objects
            
        Raises:
            requests.RequestException: If API request fails
        """
        commits = []
        page = 1
        
        while True:
            url = f"{self.BASE_URL}/users/{username}/events"
            params = {
                "page": page,
                "per_page": 100
            }
            
            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                if not data:  # No more events
                    break
                
                for event in data:
                    created_at = datetime.strptime(event["created_at"], "%Y-%m-%dT%H:%M:%SZ")
                    
                    # Only include PushEvents from 2024
                    if created_at.year != 2024 or event["type"] != "PushEvent":
                        continue
                    
                    # Extract owner and repo from repo name (format: "owner/repo")
                    owner, repo = event["repo"]["name"].split("/")
                    
                    # Get detailed commit information for each commit in the push
                    for commit_data in event["payload"]["commits"]:
                        commit = self.get_commit_details(owner, repo, commit_data["sha"])
                        if commit:
                            commits.append(commit)
                
                # Check if we should continue pagination
                # GitHub's Events API only returns up to 300 events
                if len(data) < 100 or page * 100 >= 300:
                    break
                    
                page += 1
                
            except requests.RequestException as e:
                print(f"Error fetching events: {e}", file=sys.stderr)
                raise
                
        return commits

def main():
    # Get GitHub token from environment variable
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Warning: GITHUB_TOKEN not set. API rate limits will be restricted.", file=sys.stderr)
    
    # Initialize the GitHub API client
    github = GitHubAPI(token)
    
    # Get username from command line argument or prompt
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = input("Enter GitHub username: ")
    
    try:
        events = github.get_user_events_2024(username)
        
        print(f"\nFound {len(events)} events in 2024 for user {username}")
        print("\nEvent Summary:")
        print("-" * 50)
        
        # Group events by type
        event_types = {}
        for event in events:
            event_types[event.type] = event_types.get(event.type, 0) + 1
        
        print("\nEvent Types:")
        for event_type, count in event_types.items():
            print(f"{event_type}: {count}")
            
        print("\nDetailed Events:")
        for event in events:

            print(f"\nType: {event.type}")
            print(f"Repository: {event.repo_name}")
            print(f"Date: {event.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Print relevant payload information based on event type
            if event.type == "PushEvent":
                commits = event.payload.get("commits", [])
                print(commits)
                print(f"Commits: {len(commits)}")
            elif event.type == "CreateEvent":
                print(f"Created: {event.payload.get('ref_type', 'unknown')}")
            elif event.type == "IssuesEvent":
                print(f"Action: {event.payload.get('action', 'unknown')}")
        
        commits = github.get_user_commits_2024(username)
        
        print(f"\nFound {len(commits)} commits in 2024 for user {username}")
        
        # Group commits by repository
        commits_by_repo = defaultdict(list)
        for commit in commits:
            commits_by_repo[commit.repo_name].append(commit)
        
        print("\nCommit Summary by Repository:")
        print("-" * 50)
        for repo_name, repo_commits in commits_by_repo.items():
            print(f"\nRepository: {repo_name}")
            print(f"Total commits: {len(repo_commits)}")
            
        print("\nDetailed Commit Information:")
        print("-" * 50)
        for commit in commits:
            print(f"\nRepository: {commit.repo_name}")
            print(f"Author: {commit.author_name} <{commit.author_email}>")
            print(f"Date: {commit.date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Message: {commit.message.split(chr(10))[0]}")  # First line of commit message
            print(f"URL: {commit.url}")
            if commit.stats:
                print(f"Changes: +{commit.stats.get('additions', 0)} -{commit.stats.get('deletions', 0)}")
            
    except requests.RequestException as e:
        print(f"Failed to fetch events: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()