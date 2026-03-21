"""
URL parsing utilities
"""

import re
from typing import Dict, Union
from atomgit_sdk.exceptions import URLError


def parse_atomgit_url(url: str) -> Dict[str, Union[str, int]]:
    """
    Parse AtomGit URL to extract repository and branch/PR information.

    Args:
        url: AtomGit URL (e.g., https://atomgit.com/owner/repo or https://atomgit.com/owner/repo/pulls/123)

    Returns:
        Dictionary with owner, repo, and optionally branch or pr_number

    Raises:
        URLError: If URL cannot be parsed
    """
    patterns = [
        r"atomgit\.com/([^/]+)/([^/]+)/pulls?/(\d+)",
        r"atomgit\.com/([^/]+)/([^/]+)/(tree|commits)/(.+?)(?:\?|$)",
        r"atomgit\.com/([^/]+)/([^/]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            owner = match.group(1)
            repo = match.group(2).replace(".git", "")

            if len(match.groups()) == 3 and match.group(3).isdigit():
                return {"owner": owner, "repo": repo, "pr_number": int(match.group(3))}
            elif len(match.groups()) >= 4:
                return {"owner": owner, "repo": repo, "branch": match.group(4)}
            else:
                return {"owner": owner, "repo": repo, "branch": "master"}

    raise URLError(f"Cannot parse AtomGit URL", url=url)
