"""Tests for utils module functions"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest


class TestParseKeySequence:
    """Tests for parse_key_sequence() function"""

    def test_plain_text_only(self):
        """Test plain text without special keys"""
        from activity_simulator.utils import parse_key_sequence

        result = parse_key_sequence("hello world")
        assert result == ["hello world"]

    def test_single_special_key(self):
        """Test with single special key"""
        from activity_simulator.utils import parse_key_sequence

        result = parse_key_sequence("text{Enter}")
        assert result == ["text", "Enter"]

    def test_multiple_special_keys(self):
        """Test with multiple special keys"""
        from activity_simulator.utils import parse_key_sequence

        result = parse_key_sequence("user{Tab}pass{Enter}")
        assert result == ["user", "Tab", "pass", "Enter"]

    def test_only_special_keys(self):
        """Test with only special keys"""
        from activity_simulator.utils import parse_key_sequence

        result = parse_key_sequence("{Enter}{Tab}")
        assert result == ["Enter", "Tab"]

    def test_empty_string(self):
        """Test empty string"""
        from activity_simulator.utils import parse_key_sequence

        result = parse_key_sequence("")
        assert result == []

    def test_space_between_keys(self):
        """Test with spaces between special keys"""
        from activity_simulator.utils import parse_key_sequence

        result = parse_key_sequence("{Enter} {Tab}")
        # Space becomes part of text
        assert result == ["Enter", " ", "Tab"]

    def test_unclosed_brace(self):
        """Test with unclosed brace - treated as text after split"""
        from activity_simulator.utils import parse_key_sequence

        result = parse_key_sequence("text{unclosed")
        # The { acts as a delimiter - text is split, the rest includes the {
        assert result == ["text", "{unclosed"]

    def test_multiple_special_keys_in_sequence(self):
        """Test complex sequence with many special keys"""
        from activity_simulator.utils import parse_key_sequence

        result = parse_key_sequence("{Ctrl}a{Enter}")
        assert result == ["Ctrl", "a", "Enter"]

    def test_real_password_sequence(self):
        """Test real-world password sequence"""
        from activity_simulator.utils import parse_key_sequence

        result = parse_key_sequence("mypassword{Tab}confirm{Enter}")
        assert result == ["mypassword", "Tab", "confirm", "Enter"]


class TestTimeConversions:
    """Additional tests for time conversions"""

    def test_time_str_to_minutes_edge_cases(self):
        """Test edge cases for time conversion"""
        from activity_simulator.utils import time_str_to_minutes

        # Midnight
        assert time_str_to_minutes('00:00') == 0
        # End of day
        assert time_str_to_minutes('23:59') == 1439
        # Half day
        assert time_str_to_minutes('12:00') == 720

    def test_minutes_to_time_str_edge_cases(self):
        """Test edge cases for minutes conversion"""
        from activity_simulator.utils import minutes_to_time_str

        # Midnight
        assert minutes_to_time_str(0) == '00:00'
        # End of day
        assert minutes_to_time_str(1439) == '23:59'
        # Half day
        assert minutes_to_time_str(720) == '12:00'
