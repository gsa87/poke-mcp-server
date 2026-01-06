import os
import base64
import requests
import datetime
from fastmcp import FastMCP

def register_obsidian(mcp: FastMCP):
    """
    Registers Obsidian tools using explicit mcp.add_tool() to avoid decorator issues.
    """
    
    # -- Shared Helpers --
    def get_github_config():
        token = os.environ.get("GITHUB_PERSONAL_TOKEN")
        repo = os.environ.get("OBSIDIAN_GITHUB_REPO") 
        return token, repo

    def github_request(path, params=None):
        token, repo = get_github_config()
        if not token or not repo:
            return None
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"GitHub API Error: {e}")
            return None

    # -- Tool Functions (Defined as normal Python functions) --

    def obsidian_search_notes(query: str) -> str:
        """
        Search for notes in your GitHub-synced Obsidian vault.
        Uses GitHub's code search API.
        """
        token, repo = get_github_config()
        if not token or not repo: 
            return "Error: Obsidian configuration (GITHUB_PERSONAL_TOKEN or OBSIDIAN_GITHUB_REPO) missing."
        
        search_url = "https://api.github.com/search/code"
        headers = {"Authorization": f"Bearer {token}"}
        q = f"{query} repo:{repo} extension:md"
        
        try:
            response = requests.get(search_url, headers=headers, params={"q": q}, timeout=10)
            if response.status_code == 403:
                return "Error: GitHub API rate limit exceeded or invalid token."
            
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                return "No notes found matching that text."
            
            # Return list of filenames
            return [item["path"] for item in items[:15]]
            
        except Exception as e:
            return f"Error searching GitHub: {str(e)}"

    def obsidian_read_note(filename: str) -> str:
        """
        Read the content of a specific note from GitHub.
        """
        if not filename.endswith(".md"):
            filename += ".md"
            
        token, repo = get_github_config()
        if not token: return "Error: Obsidian configuration missing."

        try:
            data = github_request(filename)
            if not data:
                return f"Error: Note '{filename}' not found in repository."
            
            if "content" not in data:
                 return "Error: File content too large or unavailable via API."

            content = base64.b64decode(data["content"]).decode("utf-8")
            return content
        except Exception as e:
            return f"Error reading note: {str(e)}"

    def obsidian_get_daily_note(date: str = None) -> str:
        """
        Get the content of a Daily Note from GitHub.
        """
        if not date:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
            
        filename = f"{date}.md" 
        return obsidian_read_note(filename)

    def obsidian_append_todo(text: str, date: str = None) -> str:
        """
        Append a To-Do to a Daily Note via GitHub API.
        """
        token, repo = get_github_config()
        if not token: return "Error: Obsidian configuration missing."

        if not date:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
            
        filename = f"{date}.md"
        
        file_data = github_request(filename)
        if not file_data:
            return f"Error: Daily note {filename} does not exist. Please create it locally first."
            
        sha = file_data["sha"]
        current_content = base64.b64decode(file_data["content"]).decode("utf-8")
        
        new_content = current_content + f"\n- [ ] {text}"
        encoded_content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
        
        url = f"https://api.github.com/repos/{repo}/contents/{filename}"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "message": f"Add todo via AI: {text}",
            "content": encoded_content,
            "sha": sha
        }
        
        try:
            requests.put(url, headers=headers, json=payload, timeout=10)
            return f"Successfully added to-do to {date}"
        except Exception as e:
            return f"Error updating file on GitHub: {str(e)}"

    # -- Explicit Registration --
    # This bypasses the decorator issue entirely
    mcp.add_tool(obsidian_search_notes)
    mcp.add_tool(obsidian_read_note)
    mcp.add_tool(obsidian_get_daily_note)
    mcp.add_tool(obsidian_append_todo)