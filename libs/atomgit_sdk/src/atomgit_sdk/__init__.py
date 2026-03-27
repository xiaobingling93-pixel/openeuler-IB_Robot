"""
AtomGit SDK - Unified AtomGit API SDK for IB_Robot

This SDK provides a unified interface for AtomGit API operations,
including PR management, code review, and repair services.
"""

__version__ = "0.1.0"

from atomgit_sdk.config import AtomGitConfig
from atomgit_sdk.client import AtomGitClient
from atomgit_sdk.models import BaseIssue, CodeIssue, ArchitectureIssue, FixResult
from atomgit_sdk.services.pr_service import PRService
from atomgit_sdk.services.issue_service import IssueService
from atomgit_sdk.exceptions import (
    AtomGitSDKError,
    AtomGitAPIError,
    ConfigurationError,
    DiffParseError,
)

__all__ = [
    "AtomGitClient",
    "AtomGitConfig",
    "BaseIssue",
    "CodeIssue",
    "ArchitectureIssue",
    "FixResult",
    "PRService",
    "IssueService",
    "AtomGitSDKError",
    "AtomGitAPIError",
    "ConfigurationError",
    "DiffParseError",
]
