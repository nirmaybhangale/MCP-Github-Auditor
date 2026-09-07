import pytest
from unittest.mock import AsyncMock, patch
from src.github_client import GitHubClient, GitHubAPIError

@pytest.mark.asyncio
async def test_get_repo_structure():
    """Test that the client correctly parses the tree response from GitHub."""
    client = GitHubClient(token="fake_test_token")
    
    # Mock the internal _request method to simulate GitHub API responses
    with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
        # We need two responses: one for default_branch, one for the tree
        mock_request.side_effect = [
            {"default_branch": "main"},
            {"tree": [{"path": "README.md"}, {"path": "src", "type": "tree"}]}
        ]
        
        result = await client.get_repo_structure("test_owner", "test_repo")
        
        assert "tree" in result
        assert len(result["tree"]) == 2
        assert result["tree"][0]["path"] == "README.md"
        assert mock_request.call_count == 2

@pytest.mark.asyncio
async def test_read_file_content_base64():
    """Test that the client correctly decodes base64 file content."""
    client = GitHubClient()
    
    with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
        # "SGVsbG8gV29ybGQ=" is "Hello World" in base64
        mock_request.return_value = {
            "encoding": "base64", 
            "content": "SGVsbG8gV29ybGQ="
        }
        
        content = await client.read_file_content("test_owner", "test_repo", "README.md")
        
        assert content == "Hello World"
        mock_request.assert_called_once_with("GET", "/repos/test_owner/test_repo/contents/README.md")

@pytest.mark.asyncio
async def test_rate_limit_error_handling():
    """Test that the client raises the correct custom exception on failure."""
    client = GitHubClient()
    
    with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = GitHubAPIError("GitHub API rate limit exceeded.")
        
        with pytest.raises(GitHubAPIError, match="rate limit"):
            await client.get_issue_details("test_owner", "test_repo")