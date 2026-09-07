import json
# Update 1: Import MCPServer instead of FastMCP
from mcp.server.mcpserver import MCPServer 
from pydantic import Field
from src.github_client import GitHubClient

# Update 2: Initialize MCPServer
mcp = MCPServer("OpenSourceAuditor")

# Initialize our GitHub API Client
github_client = GitHubClient()

@mcp.tool()
async def get_repo_structure(
    owner: str = Field(..., description="The GitHub repository owner (e.g., 'octocat')"),
    repo: str = Field(..., description="The GitHub repository name (e.g., 'Hello-World')")
) -> str:
    """Fetch the complete file tree of a GitHub repository to understand its structure."""
    try:
        tree_data = await github_client.get_repo_structure(owner, repo)
        paths = [item["path"] for item in tree_data.get("tree", [])]
        return json.dumps({"repository": f"{owner}/{repo}", "files": paths}, indent=2)
    except Exception as e:
        return f"Error fetching repository structure: {str(e)}"

@mcp.tool()
async def read_file_content(
    owner: str = Field(..., description="The GitHub repository owner"),
    repo: str = Field(..., description="The GitHub repository name"),
    path: str = Field(..., description="The exact file path within the repository (e.g., 'README')")
) -> str:
    """Fetch and read the raw content of a specific file from a GitHub repository."""
    try:
        content = await github_client.read_file_content(owner, repo, path)
        return content
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"

@mcp.tool()
async def get_issue_details(
    owner: str = Field(..., description="The GitHub repository owner"),
    repo: str = Field(..., description="The GitHub repository name"),
    state: str = Field("open", description="State of the issues ('open', 'closed', or 'all')"),
    per_page: int = Field(10, description="Number of issues to retrieve (max 100)")
) -> str:
    """Fetch recent issues from a GitHub repository to analyze bugs and tasks."""
    try:
        issues = await github_client.get_issue_details(owner, repo, state, per_page)
        summarized = [
            {
                "number": issue.get("number"),
                "title": issue.get("title"),
                "state": issue.get("state"),
                "user": issue.get("user", {}).get("login"),
                "labels": [label.get("name") for label in issue.get("labels", [])]
            }
            for issue in issues
        ]
        return json.dumps(summarized, indent=2)
    except Exception as e:
        return f"Error fetching issues: {str(e)}"

if __name__ == "__main__":
    # Run the server on standard I/O (stdio)
    mcp.run(transport='stdio')