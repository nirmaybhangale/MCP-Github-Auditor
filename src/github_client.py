import httpx
import base64
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables (useful for local testing)
load_dotenv()

class GitHubAPIError(Exception):
    """Custom exception for GitHub API failures."""
    pass

class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        # Fall back to the environment variable if a token isn't explicitly passed
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        
        # Standard GitHub API headers
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MCP-Open-Source-Auditor/1.0",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Internal helper to execute HTTP requests with error handling."""
        async with httpx.AsyncClient(headers=self.headers, base_url=self.base_url) as client:
            try:
                response = await client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                # Trap specific HTTP status codes for better debugging
                if e.response.status_code == 403 and "rate limit" in e.response.text.lower():
                    raise GitHubAPIError("GitHub API rate limit exceeded. Please configure a GITHUB_TOKEN.") from e
                if e.response.status_code == 404:
                    raise GitHubAPIError(f"Resource not found: {endpoint}") from e
                
                raise GitHubAPIError(f"GitHub API Error: {e.response.status_code} - {e.response.text}") from e
            except httpx.RequestError as e:
                raise GitHubAPIError(f"Network error during request: {str(e)}") from e

    async def get_default_branch(self, owner: str, repo: str) -> str:
        """Fetch the repository metadata to determine the default branch (e.g., main or master)."""
        data = await self._request("GET", f"/repos/{owner}/{repo}")
        return data.get("default_branch", "main")

    async def get_repo_structure(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch the complete repository file tree recursively."""
        branch = await self.get_default_branch(owner, repo)
        # Using the Git Trees API allows us to fetch the full tree efficiently
        return await self._request("GET", f"/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")

    async def read_file_content(self, owner: str, repo: str, path: str) -> str:
        """Fetch and decode the content of a specific file."""
        data = await self._request("GET", f"/repos/{owner}/{repo}/contents/{path}")
        
        if isinstance(data, list):
            raise GitHubAPIError(f"Requested path '{path}' is a directory, not a file.")
        
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8")
        elif "content" in data:
            return data["content"]
            
        raise GitHubAPIError(f"Unable to read or decode content for {path}")

    async def get_issue_details(self, owner: str, repo: str, state: str = "open", per_page: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent repository issues."""
        params = {"state": state, "per_page": per_page}
        return await self._request("GET", f"/repos/{owner}/{repo}/issues", params=params)