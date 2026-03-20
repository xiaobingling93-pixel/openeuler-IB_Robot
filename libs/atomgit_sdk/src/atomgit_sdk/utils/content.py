"""
Content manipulation utilities
"""

def add_line_numbers(content: str) -> str:
    """
    Add line number prefixes to content strings.
    
    Format: "   1 | line content"
    
    Args:
        content: The raw content string
        
    Returns:
        The content string with line number prefixes
    """
    if not content:
        return ""
        
    lines = content.split("\n")
    # Use 4-digit width for alignment, works well for most files
    return "\n".join([f"{i+1:4d} | {line}" for i, line in enumerate(lines)])
