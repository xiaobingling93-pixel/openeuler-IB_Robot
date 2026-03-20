"""
AtomGit SDK Configuration Management
"""

import json
from typing import Optional
from pydantic import BaseModel, Field
from atomgit_sdk.exceptions import ConfigurationError


class AtomGitConfig(BaseModel):
    """AtomGit API Configuration"""

    token: str = Field(..., description="AtomGit API token")
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    base_url: str = Field(
        default="https://api.atomgit.com", description="AtomGit API base URL"
    )

    class Config:
        frozen = True

    @classmethod
    def from_json(cls, config_path: str = "config.json") -> "AtomGitConfig":
        """
        Load configuration from JSON file.

        Args:
            config_path: Path to configuration file

        Returns:
            AtomGitConfig instance

        Raises:
            ConfigurationError: If required fields are missing
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except FileNotFoundError:
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")

        atomgit_section = config.get("atomgit", {})

        token = atomgit_section.get("token")
        owner = atomgit_section.get("owner")
        repo = atomgit_section.get("repo")

        if not all([token, owner, repo]):
            missing = []
            if not token:
                missing.append("token")
            if not owner:
                missing.append("owner")
            if not repo:
                missing.append("repo")
            raise ConfigurationError(
                f"Missing required configuration fields: {', '.join(missing)}"
            )

        return cls(
            token=token,
            owner=owner,
            repo=repo,
            base_url=atomgit_section.get("baseUrl", "https://api.atomgit.com"),
        )
