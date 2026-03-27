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


class TestParametricTimeChecks:
    """Параметрические тесты для функций проверки времени с разными расписаниями"""

    @pytest.mark.parametrize("schedule,current_time_minutes,expected_work", [
        # Стандартное расписание 9-18
        (
            {'work_start': '09:00', 'work_end': '18:00', 'lunch_start': '13:00', 'lunch_end': '14:00', 'breaks': []},
            540,  # 09:00
            True
        ),
        (
            {'work_start': '09:00', 'work_end': '18:00', 'lunch_start': '13:00', 'lunch_end': '14:00', 'breaks': []},
            1079,  # 17:59
            True
        ),
        (
            {'work_start': '09:00', 'work_end': '18:00', 'lunch_start': '13:00', 'lunch_end': '14:00', 'breaks': []},
            1080,  # 18:00
            True
        ),
        (
            {'work_start': '09:00', 'work_end': '18:00', 'lunch_start': '13:00', 'lunch_end': '14:00', 'breaks': []},
            1081,  # 18:01
            False
        ),
        # Раннее начало 8-17
        (
            {'work_start': '08:00', 'work_end': '17:00', 'lunch_start': '12:00', 'lunch_end': '13:00', 'breaks': []},
            480,  # 08:00
            True
        ),
        (
            {'work_start': '08:00', 'work_end': '17:00', 'lunch_start': '12:00', 'lunch_end': '13:00', 'breaks': []},
            1020,  # 17:00
            True
        ),
        (
            {'work_start': '08:00', 'work_end': '17:00', 'lunch_start': '12:00', 'lunch_end': '13:00', 'breaks': []},
            540,  # 09:00
            True
        ),
        # Позднее начало 10-19
        (
            {'work_start': '10:00', 'work_end': '19:00', 'lunch_start': '14:00', 'lunch_end': '15:00', 'breaks': []},
            600,  # 10:00
            True
        ),
        (
            {'work_start': '10:00', 'work_end': '19:00', 'lunch_start': '14:00', 'lunch_end': '15:00', 'breaks': []},
            1140,  # 19:00
            True
        ),
        (
            {'work_start': '10:00', 'work_end': '19:00', 'lunch_start': '14:00', 'lunch_end': '15:00', 'breaks': []},
            540,  # 09:00
            False
        ),
        # Короткий день (пятница) 9-16
        (
            {'work_start': '09:00', 'work_end': '16:00', 'lunch_start': '12:30', 'lunch_end': '13:30', 'breaks': []},
            540,  # 09:00
            True
        ),
        (
            {'work_start': '09:00', 'work_end': '16:00', 'lunch_start': '12:30', 'lunch_end': '13:30', 'breaks': []},
            960,  # 16:00
            True
        ),
        (
            {'work_start': '09:00', 'work_end': '16:00', 'lunch_start': '12:30', 'lunch_end': '13:30', 'breaks': []},
            961,  # 16:01
            False
        ),
    ])
    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_is_work_hours_parametric(self, mock_state, mock_time, schedule, current_time_minutes, expected_work):
        """Параметрический тест для is_work_hours с разными расписаниями"""
        mock_time.return_value = current_time_minutes

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = schedule
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_work_hours
        assert is_work_hours() is expected_work

    @pytest.mark.parametrize("schedule,current_time_minutes,expected_break,expected_type", [
        # Стандартное расписание с обедом 13-14
        (
            {'work_start': '09:00', 'work_end': '18:00', 'lunch_start': '13:00', 'lunch_end': '14:00', 'breaks': []},
            780,  # 13:00
            True,
            'обед'
        ),
        (
            {'work_start': '09:00', 'work_end': '18:00', 'lunch_start': '13:00', 'lunch_end': '14:00', 'breaks': []},
            839,  # 13:59
            True,
            'обед'
        ),
        (
            {'work_start': '09:00', 'work_end': '18:00', 'lunch_start': '13:00', 'lunch_end': '14:00', 'breaks': []},
            720,  # 12:00
            False,
            None
        ),
        (
            {'work_start': '09:00', 'work_end': '18:00', 'lunch_start': '13:00', 'lunch_end': '14:00', 'breaks': []},
            840,  # 14:00
            True,  # is_break_time использует <=, поэтому 14:00 еще в перерыве
            'обед'
        ),
        # С коротким перерывами
        (
            {
                'work_start': '09:00', 'work_end': '18:00',
                'lunch_start': '13:00', 'lunch_end': '14:00',
                'breaks': [
                    {'start': '10:30', 'end': '10:40', 'duration': 10},
                    {'start': '15:30', 'end': '15:45', 'duration': 15}
                ]
            },
            630,  # 10:30
            True,
            'перерыв'
        ),
        (
            {
                'work_start': '09:00', 'work_end': '18:00',
                'lunch_start': '13:00', 'lunch_end': '14:00',
                'breaks': [
                    {'start': '10:30', 'end': '10:40', 'duration': 10},
                    {'start': '15:30', 'end': '15:45', 'duration': 15}
                ]
            },
            639,  # 10:39
            True,
            'перерыв'
        ),
        (
            {
                'work_start': '09:00', 'work_end': '18:00',
                'lunch_start': '13:00', 'lunch_end': '14:00',
                'breaks': [
                    {'start': '10:30', 'end': '10:40', 'duration': 10},
                    {'start': '15:30', 'end': '15:45', 'duration': 15}
                ]
            },
            640,  # 10:40
            True,  # is_break_time использует <=, поэтому 10:40 еще в перерыве
            'перерыв'
        ),
        (
            {
                'work_start': '09:00', 'work_end': '18:00',
                'lunch_start': '13:00', 'lunch_end': '14:00',
                'breaks': [
                    {'start': '10:30', 'end': '10:40', 'duration': 10},
                    {'start': '15:30', 'end': '15:45', 'duration': 15}
                ]
            },
            930,  # 15:30
            True,
            'перерыв'
        ),
        (
            {
                'work_start': '09:00', 'work_end': '18:00',
                'lunch_start': '13:00', 'lunch_end': '14:00',
                'breaks': [
                    {'start': '10:30', 'end': '10:40', 'duration': 10},
                    {'start': '15:30', 'end': '15:45', 'duration': 15}
                ]
            },
            944,  # 15:44
            True,
            'перерыв'
        ),
        # Пятница с ранним обедом
        (
            {
                'work_start': '09:00', 'work_end': '16:00',
                'lunch_start': '12:00', 'lunch_end': '13:00',
                'breaks': [
                    {'start': '10:00', 'end': '10:10', 'duration': 10}
                ]
            },
            600,  # 10:00
            True,
            'перерыв'
        ),
        (
            {
                'work_start': '09:00', 'work_end': '16:00',
                'lunch_start': '12:00', 'lunch_end': '13:00',
                'breaks': [
                    {'start': '10:00', 'end': '10:10', 'duration': 10}
                ]
            },
            720,  # 12:00
            True,
            'обед'
        ),
    ])
    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_is_break_time_parametric(self, mock_state, mock_time, schedule, current_time_minutes, expected_break, expected_type):
        """Параметрический тест для is_break_time с разными расписаниями"""
        mock_time.return_value = current_time_minutes

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = schedule
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_break_time
        on_break, break_type = is_break_time()
        assert on_break is expected_break
        assert break_type == expected_type

    @pytest.mark.parametrize("schedule,current_time_minutes,expected_after_lunch", [
        # Стандартный обед 13-14
        (
            {'work_start': '09:00', 'work_end': '18:00', 'lunch_start': '13:00', 'lunch_end': '14:00', 'breaks': []},
            780,  # 13:00
            False
        ),
        (
            {'work_start': '09:00', 'work_end': '18:00', 'lunch_start': '13:00', 'lunch_end': '14:00', 'breaks': []},
            839,  # 13:59
            False
        ),
        (
            {'work_start': '09:00', 'work_end': '18:00', 'lunch_start': '13:00', 'lunch_end': '14:00', 'breaks': []},
            841,  # 14:01
            True
        ),
        (
            {'work_start': '09:00', 'work_end': '18:00', 'lunch_start': '13:00', 'lunch_end': '14:00', 'breaks': []},
            900,  # 15:00
            True
        ),
        # Ранний обед 12-13
        (
            {'work_start': '08:00', 'work_end': '17:00', 'lunch_start': '12:00', 'lunch_end': '13:00', 'breaks': []},
            720,  # 12:00
            False
        ),
        (
            {'work_start': '08:00', 'work_end': '17:00', 'lunch_start': '12:00', 'lunch_end': '13:00', 'breaks': []},
            781,  # 13:01
            True
        ),
        (
            {'work_start': '08:00', 'work_end': '17:00', 'lunch_start': '12:00', 'lunch_end': '13:00', 'breaks': []},
            1020,  # 17:00
            True
        ),
        # Поздний обед 14-15
        (
            {'work_start': '10:00', 'work_end': '19:00', 'lunch_start': '14:00', 'lunch_end': '15:00', 'breaks': []},
            840,  # 14:00
            False  # is_after_lunch использует >, поэтому 14:00 еще не "после обеда"
        ),
        (
            {'work_start': '10:00', 'work_end': '19:00', 'lunch_start': '14:00', 'lunch_end': '15:00', 'breaks': []},
            901,  # 15:01
            True
        ),
    ])
    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_is_after_lunch_parametric(self, mock_state, mock_time, schedule, current_time_minutes, expected_after_lunch):
        """Параметрический тест для is_after_lunch с разными расписаниями"""
        mock_time.return_value = current_time_minutes

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = schedule
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_after_lunch
        assert is_after_lunch() is expected_after_lunch

    @pytest.mark.parametrize("schedule,current_time_minutes,expected_before_work,expected_after_work", [
        # Стандартное расписание 9-18
        (
            {'work_start': '09:00', 'work_end': '18:00', 'lunch_start': '13:00', 'lunch_end': '14:00', 'breaks': []},
            480,  # 08:00
            True,
            False
        ),
        (
            {'work_start': '09:00', 'work_end': '18:00', 'lunch_start': '13:00', 'lunch_end': '14:00', 'breaks': []},
            540,  # 09:00
            False,
            False
        ),
        (
            {'work_start': '09:00', 'work_end': '18:00', 'lunch_start': '13:00', 'lunch_end': '14:00', 'breaks': []},
            1080,  # 18:00
            False,
            False
        ),
        (
            {'work_start': '09:00', 'work_end': '18:00', 'lunch_start': '13:00', 'lunch_end': '14:00', 'breaks': []},
            1081,  # 18:01
            False,
            True
        ),
        # Раннее начало 8-17
        (
            {'work_start': '08:00', 'work_end': '17:00', 'lunch_start': '12:00', 'lunch_end': '13:00', 'breaks': []},
            420,  # 07:00
            True,
            False
        ),
        (
            {'work_start': '08:00', 'work_end': '17:00', 'lunch_start': '12:00', 'lunch_end': '13:00', 'breaks': []},
            1020,  # 17:00
            False,
            False
        ),
        (
            {'work_start': '08:00', 'work_end': '17:00', 'lunch_start': '12:00', 'lunch_end': '13:00', 'breaks': []},
            1021,  # 17:01
            False,
            True
        ),
        # Позднее начало 10-19
        (
            {'work_start': '10:00', 'work_end': '19:00', 'lunch_start': '14:00', 'lunch_end': '15:00', 'breaks': []},
            540,  # 09:00
            True,
            False
        ),
        (
            {'work_start': '10:00', 'work_end': '19:00', 'lunch_start': '14:00', 'lunch_end': '15:00', 'breaks': []},
            1140,  # 19:00
            False,
            False
        ),
        (
            {'work_start': '10:00', 'work_end': '19:00', 'lunch_start': '14:00', 'lunch_end': '15:00', 'breaks': []},
            1141,  # 19:01
            False,
            True
        ),
    ])
    @patch('activity_simulator.simulation.time_checks.utils.get_current_time_minutes')
    @patch('activity_simulator.simulation.time_checks.get_state')
    def test_before_after_work_parametric(self, mock_state, mock_time, schedule, current_time_minutes, expected_before_work, expected_after_work):
        """Параметрический тест для is_before_work и is_after_work с разными расписаниями"""
        mock_time.return_value = current_time_minutes

        mock_state_obj = MagicMock()
        mock_state_obj.schedule = schedule
        mock_state.return_value = mock_state_obj

        from activity_simulator.simulation.time_checks import is_before_work, is_after_work
        assert is_before_work() is expected_before_work
        assert is_after_work() is expected_after_work
