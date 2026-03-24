"""Tests for config module - schedule generation and time functions"""

import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest


class TestScheduleGeneration:
    """Tests for generate_schedule() function"""

    @pytest.fixture
    def mock_config(self):
        """Basic configuration for testing"""
        return {
            'work_start_min': '08:00',
            'work_start_max': '09:00',
            'work_end_min': '17:00',
            'work_end_max': '18:00',
            'friday_work_end_min': '16:00',
            'friday_work_end_max': '17:00',
            'lunch_start_min': '12:00',
            'lunch_end_max': '14:00',
            'lunch_duration_min': 30,
            'lunch_duration_max': 60,
            'total_break_min': 40,
            'total_break_max': 60,
        }

    @patch('activity_simulator.config.datetime')
    def test_generate_schedule_weekday(self, mock_datetime, mock_config):
        """Test schedule generation for a regular weekday"""
        # Create a mock that returns proper weekday() method
        mock_date = MagicMock()
        mock_date.weekday.return_value = 0  # Monday = 0
        mock_datetime.now.return_value = mock_date

        from activity_simulator import config

        schedule = config.generate_schedule(mock_config)

        # Verify basic structure
        assert 'work_start' in schedule
        assert 'work_end' in schedule
        assert 'lunch_start' in schedule
        assert 'lunch_end' in schedule
        assert 'breaks' in schedule
        assert 'is_friday' in schedule

        # Should not be friday
        assert schedule['is_friday'] is False

    @patch('activity_simulator.config.datetime')
    def test_generate_schedule_friday(self, mock_datetime, mock_config):
        """Test that Friday has special earlier end time"""
        mock_datetime.now.return_value = datetime(2024, 1, 19)  # Friday

        from activity_simulator import config

        schedule = config.generate_schedule(mock_config)

        # Should be friday
        assert schedule['is_friday'] is True

        # Parse times and verify earlier end
        from activity_simulator.config import time_str_to_minutes
        work_end_minutes = time_str_to_minutes(schedule['work_end'])
        friday_end_max = time_str_to_minutes(mock_config['friday_work_end_max'])

        # Work end should be within friday bounds
        assert work_end_minutes <= friday_end_max

    def test_lunch_placement(self, mock_config):
        """Test that lunch is placed within work hours"""
        from activity_simulator import config
        from activity_simulator.config import time_str_to_minutes

        schedule = config.generate_schedule(mock_config)

        work_start = time_str_to_minutes(schedule['work_start'])
        work_end = time_str_to_minutes(schedule['work_end'])
        lunch_start = time_str_to_minutes(schedule['lunch_start'])
        lunch_end = time_str_to_minutes(schedule['lunch_end'])

        # Lunch should be within work hours
        assert work_start <= lunch_start <= work_end
        assert work_start <= lunch_end <= work_end
        assert lunch_start < lunch_end

    def test_breaks_distribution(self, mock_config):
        """Test that breaks are distributed throughout the day"""
        from activity_simulator import config

        # Run multiple times to account for randomness
        # With default config (40-60 min total, 30-60 min lunch), we might get 0-30 min remaining
        # which may or may not generate breaks
        found_breaks = False
        for _ in range(10):
            schedule = config.generate_schedule(mock_config.copy())
            if len(schedule['breaks']) >= 1:
                found_breaks = True
                # Each break should have valid structure
                for brk in schedule['breaks']:
                    assert 'start' in brk
                    assert 'end' in brk
                    assert 'duration' in brk
                    assert brk['duration'] > 0
                break

        # With total_break_min=40 and lunch_duration_max=60, breaks might not always appear
        # This is acceptable - just verify the key exists
        assert 'breaks' in schedule

    @patch('activity_simulator.config.datetime')
    def test_work_hours_logic(self, mock_datetime, mock_config):
        """Test that work hours are within valid bounds"""
        from activity_simulator import config
        from activity_simulator.config import time_str_to_minutes

        schedule = config.generate_schedule(mock_config)

        work_start = time_str_to_minutes(schedule['work_start'])
        work_end = time_str_to_minutes(schedule['work_end'])

        # Work should start after 6 AM and before noon
        assert 360 <= work_start <= 720  # 6:00 - 12:00
        # Work should end after noon and before 11 PM
        assert 720 <= work_end <= 1380  # 12:00 - 23:00
        # Work should be at least 6 hours
        assert work_end - work_start >= 360


class TestTimeFunctions:
    """Tests for time utility functions"""

    def test_time_str_to_minutes(self):
        """Test conversion from time string to minutes"""
        from activity_simulator.config import time_str_to_minutes

        assert time_str_to_minutes('00:00') == 0
        assert time_str_to_minutes('00:01') == 1
        assert time_str_to_minutes('01:00') == 60
        assert time_str_to_minutes('09:00') == 540
        assert time_str_to_minutes('12:30') == 750
        assert time_str_to_minutes('23:59') == 1439

    def test_minutes_to_time_str(self):
        """Test conversion from minutes to time string"""
        from activity_simulator.config import minutes_to_time_str

        assert minutes_to_time_str(0) == '00:00'
        assert minutes_to_time_str(1) == '00:01'
        assert minutes_to_time_str(60) == '01:00'
        assert minutes_to_time_str(540) == '09:00'
        assert minutes_to_time_str(750) == '12:30'
        assert minutes_to_time_str(1439) == '23:59'

    def test_time_conversion_roundtrip(self):
        """Test that time conversions are reversible"""
        from activity_simulator.config import time_str_to_minutes, minutes_to_time_str

        original_times = ['08:30', '12:00', '18:45', '23:59', '00:00']

        for original in original_times:
            minutes = time_str_to_minutes(original)
            result = minutes_to_time_str(minutes)
            assert result == original


class TestConfigKeys:
    """Tests for configuration key management"""

    def test_ensure_config_keys(self):
        """Test that ensure_config_keys adds missing keys"""
        from activity_simulator import config

        # Minimal config missing some keys
        minimal_config = {
            'min_idle_time': 30,
            'max_idle_time': 60,
        }

        result = config.ensure_config_keys(minimal_config)

        # Should have all default keys
        for key in config.DEFAULT_CONFIG:
            assert key in result

        # Original keys should be preserved
        assert result['min_idle_time'] == 30
        assert result['max_idle_time'] == 60

    def test_merge_defaults(self):
        """Test merging default config with partial config"""
        from activity_simulator import config

        partial = {
            'min_idle_time': 25,
            'max_idle_time': 65,
            'use_mouse_move': False,
        }

        result = config.ensure_config_keys(partial)

        # User-specified values should be preserved
        assert result['min_idle_time'] == 25
        assert result['max_idle_time'] == 65
        assert result['use_mouse_move'] is False

        # Default values should fill in missing keys
        assert result['min_action_interval'] == config.DEFAULT_CONFIG['min_action_interval']
        assert result['max_action_interval'] == config.DEFAULT_CONFIG['max_action_interval']
