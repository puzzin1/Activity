"""Tests for modes module"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest


class TestExecuteBurstActivity:
    """Tests for execute_burst_activity()"""

    @patch('random.choice')
    @patch('activity_simulator.simulation.modes.time.time')
    @patch('activity_simulator.simulation.modes.get_state')
    @patch('activity_simulator.simulation.modes.get_mouse_controller')
    @patch('activity_simulator.simulation.modes.log')
    @patch('random.uniform')
    def test_burst_interrupted_by_after_work_activity(self, mock_uniform, mock_log,
                                                    mock_mouse_ctrl, mock_get_state,
                                                    mock_time, mock_choice):
        """Test burst interrupted by user activity after work hours"""
        from activity_simulator.simulation.modes import execute_burst_activity

        state = Mock()
        state.config = {'use_mouse_move': True}
        state.lock = MagicMock()
        state.last_activity_time = 100
        state.user_activity_after_work = True  # User active after work
        mock_get_state.return_value = state
        mock_mouse_ctrl.return_value.position = (500, 500)

        mock_time.return_value = 200
        mock_uniform.side_effect = lambda a, b: 0.01  # Always return a value

        last_burst_time = [0]

        result = execute_burst_activity(
            last_burst_time,
            burst_interval_min=1,
            burst_interval_max=3,
            burst_duration_min=5,
            burst_duration_max=10,
            mode_name='Test',
            time_indicator='⚡',
        )

        # Should return 'interrupted'
        assert result == 'interrupted'

    @patch('random.choice')
    @patch('activity_simulator.simulation.modes.time.time')
    @patch('activity_simulator.simulation.modes.get_state')
    @patch('activity_simulator.simulation.modes.get_mouse_controller')
    @patch('activity_simulator.simulation.modes.log')
    @patch('random.uniform')
    def test_burst_break_ended(self, mock_uniform, mock_log, mock_mouse_ctrl,
                               mock_get_state, mock_time, mock_choice):
        """Test burst ends when break period ends"""
        from activity_simulator.simulation.modes import execute_burst_activity

        state = Mock()
        state.config = {'use_mouse_move': True}
        state.lock = MagicMock()
        state.last_activity_time = 100
        state.user_activity_after_work = False
        mock_get_state.return_value = state
        mock_mouse_ctrl.return_value.position = (500, 500)

        mock_time.return_value = 200
        mock_uniform.side_effect = lambda a, b: 0.01

        # Mock check_break_ended to return False (break ended)
        check_break_ended = Mock(return_value=(False, None))

        last_burst_time = [0]

        result = execute_burst_activity(
            last_burst_time,
            burst_interval_min=1,
            burst_interval_max=3,
            burst_duration_min=5,
            burst_duration_max=10,
            mode_name='Test',
            time_indicator='⚡',
            check_break_ended=check_break_ended,
        )

        # Should return 'ended'
        assert result == 'ended'
        assert check_break_ended.called

    @patch('random.choice')
    @patch('activity_simulator.simulation.modes.time.time')
    @patch('activity_simulator.simulation.modes.get_state')
    @patch('activity_simulator.simulation.modes.get_mouse_controller')
    @patch('activity_simulator.simulation.modes.log')
    @patch('random.uniform')
    def test_burst_waiting_for_user_activity_delay(self, mock_uniform, mock_log,
                                                 mock_mouse_ctrl, mock_get_state,
                                                 mock_time, mock_choice):
        """Test burst waits when user was recently active"""
        from activity_simulator.simulation.modes import execute_burst_activity

        state = Mock()
        state.config = {'use_mouse_move': True}
        state.lock = MagicMock()
        # User was active 30 seconds ago (less than MINIMUM_DELAY_AFTER_USER_ACTIVITY)
        state.last_activity_time = 200
        state.user_activity_after_work = False
        mock_get_state.return_value = state
        mock_mouse_ctrl.return_value.position = (500, 500)

        mock_time.return_value = 230  # 30 seconds after last activity
        mock_uniform.side_effect = lambda a, b: 0.01

        last_burst_time = [0]

        result = execute_burst_activity(
            last_burst_time,
            burst_interval_min=1,
            burst_interval_max=3,
            burst_duration_min=5,
            burst_duration_max=10,
            mode_name='Test',
            time_indicator='⚡',
        )

        # Should return 'waiting' (user was active within last 60 seconds)
        assert result == 'waiting'
