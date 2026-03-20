"""
Custom exceptions for AtomGit SDK
"""

from typing import Optional


class AtomGitSDKError(Exception):
    """Base exception for AtomGit SDK"""

    pass


class AtomGitAPIError(AtomGitSDKError):
    """Exception raised for AtomGit API errors"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(self.message)

    def __str__(self):
        if self.status_code:
            return f"AtomGit API Error ({self.status_code}): {self.message}"
        return f"AtomGit API Error: {self.message}"


class ConfigurationError(AtomGitSDKError):
    """Exception raised for configuration errors"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"Configuration Error: {self.message}"


class DiffParseError(AtomGitSDKError):
    """Exception raised for diff parsing errors"""

    def __init__(self, message: str, patch_content: Optional[str] = None):
        self.message = message
        self.patch_content = patch_content
        super().__init__(self.message)

    def __str__(self):
        return f"Diff Parse Error: {self.message}"


class URLError(AtomGitSDKError):
    """Exception raised for URL parsing errors"""

    def __init__(self, message: str, url: Optional[str] = None):
        self.message = message
        self.url = url
        super().__init__(self.message)

    def __str__(self):
        if self.url:
            return f"URL Error: {self.message} (URL: {self.url})"
        return f"URL Error: {self.message}"
