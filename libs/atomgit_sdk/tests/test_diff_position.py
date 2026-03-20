#!/usr/bin/env python3
"""
Comprehensive tests for calculate_diff_position algorithm.

This is the MOST CRITICAL test because the SDK heavily depends on this algorithm.
"""

import pytest
from atomgit_sdk.utils.diff import calculate_diff_position


class TestCalculateDiffPosition:
    """Test suite for diff position calculation"""

    def test_simple_modification(self):
        """Test basic single-line modification"""
        patch = """@@ -10,5 +10,6 @@
 context line 1
 context line 2
-old line
+new line
 context line 3"""
        # Line 10 is context line 1
        assert calculate_diff_position(patch, 10, is_new_file=False) == 1
        # Line 11 is context line 2
        assert calculate_diff_position(patch, 11, is_new_file=False) == 2
        # Line 12 is the new line (+new line)
        assert calculate_diff_position(patch, 12, is_new_file=False) == 4
        # Line 13 is context line 3
        assert calculate_diff_position(patch, 13, is_new_file=False) == 5

    def test_new_file(self):
        """Test new file (no previous version)"""
        patch = ""
        line_number = 5
        position = calculate_diff_position(patch, line_number, is_new_file=True)
        assert position == line_number

    def test_empty_patch_not_new_file(self):
        """Test empty patch when not a new file"""
        patch = ""
        line_number = 10
        position = calculate_diff_position(patch, line_number, is_new_file=False)
        assert position is None

    def test_invalid_line_zero(self):
        """Test line number 0"""
        patch = "@@ -1,3 +1,3 @@\n line1\n line2\n line3"
        position = calculate_diff_position(patch, 0, is_new_file=False)
        assert position is None

    def test_invalid_line_negative(self):
        """Test negative line number"""
        patch = "@@ -1,3 +1,3 @@\n line1\n line2\n line3"
        position = calculate_diff_position(patch, -1, is_new_file=False)
        assert position is None

    def test_multiple_hunks(self):
        """Test multiple hunks in same patch"""
        patch = """@@ -10,3 +10,4 @@
 first hunk line 1
+first addition
 end first

@@ -20,3 +20,4 @@
 second hunk line 1
+second addition
 end second"""
        # Line 22 should be "second addition"
        position = calculate_diff_position(patch, 22, is_new_file=False)
        assert position is not None

    def test_line_in_context(self):
        """Test line that's only context (not added/removed)"""
        patch = """@@ -10,3 +10,3 @@
 context line 1
 context line 2
 context line 3"""
        # Line 12 is a context line
        position = calculate_diff_position(patch, 12, is_new_file=False)
        assert position is not None

    def test_line_before_hunk(self):
        """Test line number before first hunk"""
        patch = """@@ -10,3 +10,3 @@
 line 10
 line 11
 line 12"""
        # Line 5 doesn't exist in this diff
        position = calculate_diff_position(patch, 5, is_new_file=False)
        assert position is None

    def test_line_after_last_hunk(self):
        """Test line number after last hunk"""
        patch = """@@ -10,3 +10,3 @@
 line 10
 line 11
 line 12"""
        # Line 20 doesn't exist in this diff
        position = calculate_diff_position(patch, 20, is_new_file=False)
        assert position is None

    def test_removed_line(self):
        """Test line that was removed (should not be found)"""
        patch = """@@ -10,3 +10,2 @@
 context line
-removed line
 context line"""
        # Line 10 exists
        assert calculate_diff_position(patch, 10, is_new_file=False) == 1
        # Line 11 exists (it's the second 'context line')
        assert calculate_diff_position(patch, 11, is_new_file=False) == 3
        # Line 12 does NOT exist in the new file (hunk size is 2)
        assert calculate_diff_position(patch, 12, is_new_file=False) is None

    def test_large_hunk(self):
        """Test large hunk with many lines"""
        # Add a space before each line to make it valid diff context
        patch = """@@ -1,100 +1,101 @@\n""" + "\n".join([f" line {i}" for i in range(1, 101)]) + "\n+addition"
        # Line 100 is the last context line
        assert calculate_diff_position(patch, 100, is_new_file=False) == 100
        # Line 101 is the addition
        assert calculate_diff_position(patch, 101, is_new_file=False) == 101

    def test_weird_line_numbers_in_hunk_header(self):
        """Test hunk header with non-standard line numbers"""
        patch = """@@ -999,3 +999,4 @@
 line 999
+new line
 line 1000"""
        position = calculate_diff_position(patch, 1000, is_new_file=False)
        assert position is not None

    def test_mixed_additions_and_context(self):
        """Test patch with both additions and context lines"""
        patch = """@@ -10,5 +10,7 @@
 context 1
+addition 1
 context 2
+addition 2
 context 3"""
        # Test addition 2 (line 14)
        position = calculate_diff_position(patch, 14, is_new_file=False)
        assert position is not None

    def test_no_new_line_marker(self):
        """Test patch without +new_line marker (should use hunk start)"""
        patch = """@@ -10,3 +10,3 @@
 line 10
 line 11
 line 12"""
        position = calculate_diff_position(patch, 11, is_new_file=False)
        assert position is not None

    def test_malformed_hunk_header(self):
        """Test patch with malformed hunk header"""
        patch = """@@ malformed @@
 line 1
 line 2"""
        # Should return None because hunk header is malformed
        position = calculate_diff_position(patch, 1, is_new_file=False)
        assert position is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
