"""
Data models for AtomGit SDK
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class BaseIssue(BaseModel):
    """Base class for issues"""

    file: str = Field(..., description="File path")
    line: int = Field(..., description="Line number")
    title: str = Field(..., description="Issue title")
    description: str = Field(..., description="Issue description")
    severity: str = Field(default="warning", description="Issue severity")

    class Config:
        frozen = False


class CodeIssue(BaseIssue):
    """Code issue model"""

    type: str = Field(
        default="bug", description="Issue type (bug, security, performance, etc.)"
    )
    confidence: int = Field(
        default=80, ge=0, le=100, description="Confidence score (0-100)"
    )
    context_code: Optional[str] = Field(
        default=None, description="Context code snippet"
    )
    fix_code: Optional[str] = Field(default=None, description="Fix code snippet")
    fix_explanation: Optional[str] = Field(default=None, description="Fix explanation")


class ArchitectureIssue(BaseIssue):
    """Architecture issue model"""

    pillar: str = Field(
        default="python",
        description="Architecture pillar (ssot, contract, control_mode, etc.)",
    )
    context_code: Optional[str] = Field(
        default=None, description="Context code snippet"
    )
    fix: Optional[str] = Field(default=None, description="Fix suggestion")


class FixResult(BaseModel):
    """Fix result model for repair operations"""

    has_fix: bool = Field(default=False, description="Whether a fix is available")
    needs_reply_only: bool = Field(
        default=False, description="Only needs reply, no code fix"
    )
    needs_revert_file: bool = Field(
        default=False, description="Needs to revert entire file"
    )
    needs_delete_lines: bool = Field(
        default=False, description="Needs to delete specific lines"
    )
    file_path: str = Field(default="", description="File path to fix")
    delete_lines: List[int] = Field(default_factory=list, description="Lines to delete")
    fix_description: str = Field(default="", description="Fix description")
    original_code: str = Field(default="", description="Original code")
    fixed_code: str = Field(default="", description="Fixed code")
    reason: str = Field(default="", description="Reason for fix or reply")
