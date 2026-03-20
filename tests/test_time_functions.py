"""Tests for time-related functions in simulation module"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest


class TestIsWorkHours:
    """Tests for is_work_hours() function"""

    @pytest.fixture
    def setup_schedule(self):
        """Setup schedule for testing"""
        from activity_simulator import simulation
        simulation.SCHEDULE = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        }
        simulation.CONFIG = {'afterhours_mode': 'disabled'}
        return simulation

    @patch('activity_simulator.simulation.utils.get_current_time_minutes')
    def test_within_work_hours(self, mock_time, setup_schedule):
        """Test when current time is within work hours"""
        mock_time.return_value = 600  # 10:00

        from activity_simulator import simulation
        assert simulation.is_work_hours() is True

    @patch('activity_simulator.simulation.utils.get_current_time_minutes')
    def test_before_work_hours(self, mock_time, setup_schedule):
        """Test when current time is before work hours"""
        mock_time.return_value = 480  # 08:00

        from activity_simulator import simulation
        assert simulation.is_work_hours() is False

    @patch('activity_simulator.simulation.utils.get_current_time_minutes')
    def test_after_work_hours(self, mock_time, setup_schedule):
        """Test when current time is after work hours"""
        mock_time.return_value = 1140  # 19:00

        from activity_simulator import simulation
        assert simulation.is_work_hours() is False

    @patch('activity_simulator.simulation.utils.get_current_time_minutes')
    def test_at_work_start_boundary(self, mock_time, setup_schedule):
        """Test at exact work start time"""
        mock_time.return_value = 540  # 09:00

        from activity_simulator import simulation
        assert simulation.is_work_hours() is True

    @patch('activity_simulator.simulation.utils.get_current_time_minutes')
    def test_at_work_end_boundary(self, mock_time, setup_schedule):
        """Test at exact work end time"""
        mock_time.return_value = 1080  # 18:00

        from activity_simulator import simulation
        assert simulation.is_work_hours() is True


class TestIsBreakTime:
    """Tests for is_break_time() function"""

    @pytest.fixture
    def setup_schedule(self):
        """Setup schedule for testing"""
        from activity_simulator import simulation
        simulation.SCHEDULE = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': [
                {'start': '10:30', 'end': '10:40', 'duration': 10},
                {'start': '15:30', 'end': '15:40', 'duration': 10}
            ]
        }
        return simulation

    @patch('activity_simulator.simulation.utils.get_current_time_minutes')
    def test_during_lunch(self, mock_time, setup_schedule):
        """Test during lunch break"""
        mock_time.return_value = 780  # 13:00

        from activity_simulator import simulation
        on_break, break_type = simulation.is_break_time()

        assert on_break is True
        assert break_type == 'обед'

    @patch('activity_simulator.simulation.utils.get_current_time_minutes')
    def test_during_short_break(self, mock_time, setup_schedule):
        """Test during short break - 10:30 = 10*60+30 = 630 minutes"""
        mock_time.return_value = 630  # 10:30

        from activity_simulator import simulation
        on_break, break_type = simulation.is_break_time()

        assert on_break is True
        assert break_type == 'перерыв'

    @patch('activity_simulator.simulation.utils.get_current_time_minutes')
    def test_not_on_break(self, mock_time, setup_schedule):
        """Test when not on break"""
        mock_time.return_value = 720  # 12:00

        from activity_simulator import simulation
        on_break, break_type = simulation.is_break_time()

        assert on_break is False
        assert break_type is None


class TestIsAfterWork:
    """Tests for is_after_work() function"""

    @pytest.fixture
    def setup_schedule(self):
        """Setup schedule for testing"""
        from activity_simulator import simulation
        simulation.SCHEDULE = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        }
        return simulation

    @patch('activity_simulator.simulation.utils.get_current_time_minutes')
    def test_after_work(self, mock_time, setup_schedule):
        """Test when after work"""
        mock_time.return_value = 1100  # 18:20

        from activity_simulator import simulation
        assert simulation.is_after_work() is True

    @patch('activity_simulator.simulation.utils.get_current_time_minutes')
    def test_before_work(self, mock_time, setup_schedule):
        """Test when before work"""
        mock_time.return_value = 480  # 08:00

        from activity_simulator import simulation
        assert simulation.is_after_work() is False


class TestShouldSimulateAfterhours:
    """Tests for should_simulate_afterhours() function"""

    @pytest.fixture
    def setup(self):
        """Setup modules"""
        from activity_simulator import simulation
        simulation.SCHEDULE = {
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        }
        return simulation

    @patch('activity_simulator.simulation.is_before_work')
    @patch('activity_simulator.simulation.is_work_hours')
    def test_disabled_mode(self, mock_work, mock_before, setup):
        """Test disabled mode returns False"""
        from activity_simulator import simulation

        simulation.CONFIG = {'afterhours_mode': 'disabled'}
        simulation.is_before_work = MagicMock(return_value=False)
        simulation.is_work_hours = MagicMock(return_value=False)

        assert simulation.should_simulate_afterhours() is False

    @patch('activity_simulator.simulation.is_before_work')
    @patch('activity_simulator.simulation.is_work_hours')
    def test_before_only_mode(self, mock_work, mock_before, setup):
        """Test before_only mode"""
        from activity_simulator import simulation

        simulation.CONFIG = {'afterhours_mode': 'before_only'}
        simulation.is_before_work = MagicMock(return_value=True)
        simulation.is_work_hours = MagicMock(return_value=False)

        assert simulation.should_simulate_afterhours() is True

    @patch('activity_simulator.simulation.is_work_hours')
    def test_before_and_after_mode(self, mock_work, setup):
        """Test before_and_after mode"""
        from activity_simulator import simulation

        simulation.CONFIG = {'afterhours_mode': 'before_and_after'}
        simulation.is_work_hours = MagicMock(return_value=False)

        assert simulation.should_simulate_afterhours() is True

    @patch('activity_simulator.simulation.is_work_hours')
    def test_before_and_after_mode_during_work(self, mock_work, setup):
        """Test before_and_after mode during work hours returns False"""
        from activity_simulator import simulation

        simulation.CONFIG = {'afterhours_mode': 'before_and_after'}
        simulation.is_work_hours = MagicMock(return_value=True)

        assert simulation.should_simulate_afterhours() is False
