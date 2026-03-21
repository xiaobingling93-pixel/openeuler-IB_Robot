"""
Diff parsing utilities
"""

import re
from typing import Optional
from atomgit_sdk.exceptions import DiffParseError


def calculate_diff_position(
    patch: str, line_number: int, is_new_file: bool = False
) -> Optional[int]:
    """
    Calculate the position in a diff for a given file line number.

    This maps the actual line number in the file to the position in the diff,
    which is required for AtomGit API inline comments.

    Args:
        patch: The diff patch content
        line_number: The actual line number in the file (1-indexed)
        is_new_file: Whether this is a new file (no previous version)

    Returns:
        The position in the diff, or None if the line cannot be mapped

    Raises:
        DiffParseError: If patch is malformed
    """
    if not patch:
        return line_number if is_new_file else None

    if not line_number or line_number <= 0:
        return None

    lines = patch.split("\n")
    position = 0
    current_new_line = 0
    in_hunk = False

    for line in lines:
        hunk_match = re.match(r"^@@\s+-\d+,?\d*\s+\+(\d+),?\d*\s+@@", line)
        if hunk_match:
            if not in_hunk:
                in_hunk = True
                position = 0
            else:
                position += 1
            current_new_line = int(hunk_match.group(1)) - 1
            continue

        if not in_hunk:
            continue

        position += 1
        first_char = line[0] if line else ""

        if first_char == "+":
            current_new_line += 1
            if current_new_line == line_number:
                return position
        elif first_char == " ":
            current_new_line += 1
            if current_new_line == line_number:
                return position

    if is_new_file:
        return line_number

    return None
