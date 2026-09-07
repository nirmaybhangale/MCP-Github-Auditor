import json
import os
from pathlib import Path
from mcp.server.mcpserver import MCPServer 
from pydantic import Field
from src.github_client import GitHubClient

#Define the secure sandboxed directory for side effects ---
REPORTS_DIR = Path.cwd() / "audit_reports"
REPORTS_DIR.mkdir(exist_ok=True) # Create the directory if it doesn't exist

#Initialize MCPServer
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


@mcp.tool()
async def save_audit_report(
    filename: str = Field(..., description="The name of the file to save (e.g., 'react_audit.md')"),
    content: str = Field(..., description="The full markdown content of the codebase audit.")
) -> str:
    """
    SIDE EFFECT: Saves the generated audit report to the local file system.
    """
    # 1. Refusal Boundary: Extension Check
    if not filename.endswith(".md"):
        return "REFUSED: System policy only permits saving Markdown (.md) files to prevent executable code injection."
    
    try:
        # Resolve the absolute path
        file_path = (REPORTS_DIR / filename).resolve()
        
        # 2. Input Validation & Refusal Boundary: Path Traversal Check
        # This prevents a malicious LLM payload from passing filename="../../windows/system32/hack.md"
        if not file_path.is_relative_to(REPORTS_DIR.resolve()):
            return "REFUSED: Path traversal detected. You are strictly sandboxed to the audit_reports directory."
            
        # 3. The Side Effect: State Mutation
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return f"SUCCESS: Audit report securely saved to {file_path}"
        
    except Exception as e:
        return f"ERROR: Failed to write file due to system error: {str(e)}"

if __name__ == "__main__":
    # Run the server on standard I/O (stdio)
    mcp.run(transport='stdio')