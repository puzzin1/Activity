"""Tests for time-related functions in simulation module"""

import sys
import os
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest


class TestIsWorkHours:
    """Tests for is_work_hours() function"""

    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_within_work_hours(self, mock_state, mock_time):
        """Test when current time is within work hours"""
        mock_time.return_value = 600  # 10:00

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        }
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_work_hours
        assert is_work_hours() is True

    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_before_work_hours(self, mock_state, mock_time):
        """Test when current time is before work hours"""
        mock_time.return_value = 480  # 08:00

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        }
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_work_hours
        assert is_work_hours() is False

    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_after_work_hours(self, mock_state, mock_time):
        """Test when current time is after work hours"""
        mock_time.return_value = 1140  # 19:00

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        }
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_work_hours
        assert is_work_hours() is False

    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_at_work_start_boundary(self, mock_state, mock_time):
        """Test at exact work start time"""
        mock_time.return_value = 540  # 09:00

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        }
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_work_hours
        assert is_work_hours() is True

    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_at_work_end_boundary(self, mock_state, mock_time):
        """Test at exact work end time"""
        mock_time.return_value = 1080  # 18:00

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        }
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_work_hours
        assert is_work_hours() is True


class TestIsBreakTime:
    """Tests for is_break_time() function"""

    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_during_lunch(self, mock_state, mock_time):
        """Test during lunch break"""
        mock_time.return_value = 780  # 13:00

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        }
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_break_time
        on_break, break_type = is_break_time()

        assert on_break is True
        assert break_type == 'обед'

    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_during_short_break(self, mock_state, mock_time):
        """Test during short break - 10:30 = 10*60+30 = 630 minutes"""
        mock_time.return_value = 630  # 10:30

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': [
                {'start': '10:30', 'end': '10:40', 'duration': 10},
                {'start': '15:30', 'end': '15:40', 'duration': 10}
            ]
        }
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_break_time
        on_break, break_type = is_break_time()

        assert on_break is True
        assert break_type == 'перерыв'

    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_not_on_break(self, mock_state, mock_time):
        """Test when not on break"""
        mock_time.return_value = 720  # 12:00

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        }
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_break_time
        on_break, break_type = is_break_time()

        assert on_break is False
        assert break_type is None


class TestIsAfterWork:
    """Tests for is_after_work() function"""

    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_after_work(self, mock_state, mock_time):
        """Test when after work"""
        mock_time.return_value = 1100  # 18:20

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        }
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_after_work
        assert is_after_work() is True

    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_before_work(self, mock_state, mock_time):
        """Test when before work"""
        mock_time.return_value = 480  # 08:00

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        }
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_after_work
        assert is_after_work() is False


class TestIsBeforeWork:
    """Tests for is_before_work() function"""

    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_before_work(self, mock_state, mock_time):
        """Test when before work"""
        mock_time.return_value = 480  # 08:00

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        }
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_before_work
        assert is_before_work() is True

    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_during_work(self, mock_state, mock_time):
        """Test when during work hours"""
        mock_time.return_value = 600  # 10:00

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        }
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_before_work
        assert is_before_work() is False


class TestShouldSimulateAfterhours:
    """Tests for should_simulate_afterhours() function"""

    @patch('activity_simulator.simulation.time_checks.get_state')
    @patch('activity_simulator.simulation.time_checks.is_before_work')
    @patch('activity_simulator.simulation.time_checks.is_work_hours')
    def test_disabled_mode(self, mock_work, mock_before, mock_state):
        """Test disabled mode returns False"""
        mock_state_obj = MagicMock()
        mock_state_obj.config = {'afterhours_mode': 'disabled'}
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import should_simulate_afterhours
        assert should_simulate_afterhours() is False

    @patch('activity_simulator.simulation.time_checks.get_state')
    @patch('activity_simulator.simulation.time_checks.is_before_work')
    @patch('activity_simulator.simulation.time_checks.is_work_hours')
    def test_before_only_mode_before_work(self, mock_work, mock_before, mock_state):
        """Test before_only mode when before work"""
        mock_state_obj = MagicMock()
        mock_state_obj.config = {'afterhours_mode': 'before_only'}
        mock_state.return_value = mock_state_obj
        mock_before.return_value = True
        mock_work.return_value = False

        from activity_simulator.simulation.time_checks import should_simulate_afterhours
        assert should_simulate_afterhours() is True

    @patch('activity_simulator.simulation.time_checks.get_state')
    @patch('activity_simulator.simulation.time_checks.is_before_work')
    @patch('activity_simulator.simulation.time_checks.is_work_hours')
    def test_before_only_mode_after_work(self, mock_work, mock_before, mock_state):
        """Test before_only mode when after work returns False"""
        mock_state_obj = MagicMock()
        mock_state_obj.config = {'afterhours_mode': 'before_only'}
        mock_state.return_value = mock_state_obj
        mock_before.return_value = False
        mock_work.return_value = False

        from activity_simulator.simulation.time_checks import should_simulate_afterhours
        assert should_simulate_afterhours() is False

    @patch('activity_simulator.simulation.time_checks.get_state')
    @patch('activity_simulator.simulation.time_checks.is_work_hours')
    def test_before_and_after_mode(self, mock_work, mock_state):
        """Test before_and_after mode"""
        mock_state_obj = MagicMock()
        mock_state_obj.config = {'afterhours_mode': 'before_and_after'}
        mock_state.return_value = mock_state_obj
        mock_work.return_value = False

        from activity_simulator.simulation.time_checks import should_simulate_afterhours
        assert should_simulate_afterhours() is True

    @patch('activity_simulator.simulation.time_checks.get_state')
    @patch('activity_simulator.simulation.time_checks.is_work_hours')
    def test_before_and_after_mode_during_work(self, mock_work, mock_state):
        """Test before_and_after mode during work hours returns False"""
        mock_state_obj = MagicMock()
        mock_state_obj.config = {'afterhours_mode': 'before_and_after'}
        mock_state.return_value = mock_state_obj
        mock_work.return_value = True

        from activity_simulator.simulation.time_checks import should_simulate_afterhours
        assert should_simulate_afterhours() is False


class TestIsAfterLunch:
    """Tests for is_after_lunch() function"""

    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_after_lunch(self, mock_state, mock_time):
        """Test when after lunch"""
        mock_time.return_value = 900  # 15:00

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        }
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_after_lunch
        assert is_after_lunch() is True

    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_during_lunch(self, mock_state, mock_time):
        """Test when during lunch"""
        mock_time.return_value = 780  # 13:00

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        }
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_after_lunch
        assert is_after_lunch() is False
