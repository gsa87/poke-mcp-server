import os
import base64
import requests
import datetime
from fastmcp import FastMCP

def register_obsidian(mcp: FastMCP):
    """
    Registers Obsidian tools that read from a private GitHub Repository.
    This allows the AI to access your notes from the cloud (Render) without your laptop being on.
    """
    
    def get_github_config():
        token = os.environ.get("GITHUB_PERSONAL_TOKEN")
        repo = os.environ.get("OBSIDIAN_GITHUB_REPO") # Format: "username/repo-name"
        
        if not token or not repo:
            # We log a warning but don't crash immediately, to allow other tools to work
            print("WARNING: Obsidian env vars missing. Obsidian tools will fail if called.")
            return None, None
            
        return token, repo

    def github_request(path, params=None):
        token, repo = get_github_config()
        if not token:
            return None
            
        # GitHub Content API
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

    @mcp.tool
    def obsidian_search_notes(query: str):
        """
        Search for notes in your GitHub-synced Obsidian vault.
        Uses GitHub's code search API to find matching files.
        """
        token, repo = get_github_config()
        if not token: return "Error: Obsidian configuration missing."
        
        # GitHub Code Search API is different from Contents API
        search_url = "https://api.github.com/search/code"
        headers = {"Authorization": f"Bearer {token}"}
        
        # Construct search query: "text repo:user/repo extension:md"
        q = f"{query} repo:{repo} extension:md"
        
        try:
            response = requests.get(search_url, headers=headers, params={"q": q}, timeout=10)
            if response.status_code == 403:
                return "Error: GitHub API rate limit exceeded or invalid token permissions."
                
            response.raise_for_status()
            data = response.json()
            
            items = data.get("items", [])
            if not items:
                return "No notes found matching that text."
            
            # Return list of filenames/paths
            results = [item["path"] for item in items[:15]]
            return results
            
        except Exception as e:
            return f"Error searching GitHub: {str(e)}"

    @mcp.tool
    def obsidian_read_note(filename: str):
        """
        Read the content of a specific note from GitHub.
        
        Args:
            filename: The path to the file (e.g., "Daily Notes/2024-01-01.md").
        """
        # Ensure extension
        if not filename.endswith(".md"):
            filename += ".md"
            
        try:
            data = github_request(filename)
            if not data:
                return f"Error: Note '{filename}' not found in repository."
            
            # GitHub API returns content base64 encoded
            # 'content' field might be missing if file is too large ( > 1MB), then we need 'blob' API.
            # But for notes, usually 'content' is there.
            if "content" not in data:
                 return "Error: File content not available directly (too large?)."

            content = base64.b64decode(data["content"]).decode("utf-8")
            return content
            
        except Exception as e:
            return f"Error reading note from GitHub: {str(e)}"

    @mcp.tool
    def obsidian_get_daily_note(date: str = None):
        """
        Get the content of a Daily Note from GitHub.
        
        Args:
            date: (Optional) Date in YYYY-MM-DD format. Defaults to today.
        """
        if not date:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
            
        # IMPORTANT: Adjust this path to match your actual Obsidian folder structure!
        # Assuming format "YYYY-MM-DD.md" in root or specific folder
        # If standard Obsidian Daily Notes: usually in root or a folder.
        # Let's try root first, or you can edit this path.
        filename = f"{date}.md" 
        
        return obsidian_read_note(filename)

    @mcp.tool
    def obsidian_append_todo(text: str, date: str = None):
        """
        Append a To-Do to a Daily Note via GitHub API.
        """
        token, repo = get_github_config()
        if not token: return "Error: Obsidian configuration missing."

        if not date:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
            
        # IMPORTANT: Adjust this path to match your folder structure
        filename = f"{date}.md"
        
        # 1. Get current file sha (needed for update)
        file_data = github_request(filename)
        if not file_data:
            return f"Error: Daily note {filename} does not exist. Please create it locally first."
            
        sha = file_data["sha"]
        if "content" not in file_data:
             return "Error: Cannot read file to append (too large?)."

        current_content = base64.b64decode(file_data["content"]).decode("utf-8")
        
        # 2. Append text
        new_content = current_content + f"\n- [ ] {text}"
        encoded_content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
        
        # 3. Push update
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