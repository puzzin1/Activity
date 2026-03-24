"""Tests for listeners module"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest


class TestOnKeyboardEvent:
    """Tests for on_keyboard_event()"""

    @patch('activity_simulator.listeners.simulation')
    def test_basic_keyboard_event(self, mock_sim):
        """Test basic keyboard event updates state"""
        from activity_simulator.listeners import on_keyboard_event

        state = Mock()
        state.lock = MagicMock()
        state.is_performing_action = False
        state.last_activity_time = 0
        state.current_idle_threshold = 100
        state.is_simulating = True
        state.absolute_anchor_position = (500, 500)
        mock_sim.get_state.return_value = state
        mock_sim.is_after_work.return_value = False
        mock_sim.is_work_hours.return_value = True
        mock_sim.log = Mock()

        on_keyboard_event(Mock())

        # Check that state was updated
        assert state.last_activity_time > 0
        assert state.current_idle_threshold is None
        assert state.is_simulating is False
        assert state.absolute_anchor_position is None

    @patch('activity_simulator.listeners.simulation')
    def test_keyboard_event_during_simulation(self, mock_sim):
        """Test keyboard event during simulation is ignored"""
        from activity_simulator.listeners import on_keyboard_event

        state = Mock()
        state.lock = MagicMock()
        state.is_performing_action = True  # Simulation in progress
        state.last_activity_time = time.time() - 30
        mock_sim.get_state.return_value = state
        mock_sim.log = Mock()

        old_time = state.last_activity_time

        on_keyboard_event(Mock())

        # Time should not be updated (simulated event ignored)
        assert state.last_activity_time == old_time
        mock_sim.log.assert_called_once()

    @patch('activity_simulator.listeners.simulation')
    def test_keyboard_event_after_work(self, mock_sim):
        """Test keyboard event after work hours sets flag"""
        from activity_simulator.listeners import on_keyboard_event

        state = Mock()
        state.lock = MagicMock()
        state.is_performing_action = False
        state.user_activity_after_work = False
        mock_sim.get_state.return_value = state
        mock_sim.is_after_work.return_value = True
        mock_sim.is_work_hours.return_value = False
        mock_sim.log = Mock()

        on_keyboard_event(Mock())

        # Check that after work flag was set
        assert state.user_activity_after_work is True


class TestOnMouseEvent:
    """Tests for on_mouse_event()"""

    @patch('activity_simulator.listeners.simulation')
    def test_basic_mouse_event(self, mock_sim):
        """Test basic mouse event updates state"""
        from activity_simulator.listeners import on_mouse_event

        state = Mock()
        state.lock = MagicMock()
        state.is_performing_action = False
        state.last_activity_time = 0
        state.initial_mouse_position = (0, 0)
        state.current_idle_threshold = 100
        state.is_simulating = True
        state.absolute_anchor_position = (500, 500)
        state.last_mouse_log_time = 0
        mock_sim.get_state.return_value = state
        mock_sim.is_after_work.return_value = False
        mock_sim.is_work_hours.return_value = True
        mock_sim.log = Mock()

        on_mouse_event(100, 200)

        # Check that state was updated
        assert state.last_activity_time > 0
        assert state.initial_mouse_position == (100, 200)
        assert state.current_idle_threshold is None
        assert state.is_simulating is False
        assert state.absolute_anchor_position is None

    @patch('activity_simulator.listeners.simulation')
    def test_mouse_event_during_simulation(self, mock_sim):
        """Test mouse event during simulation is ignored"""
        from activity_simulator.listeners import on_mouse_event

        state = Mock()
        state.lock = MagicMock()
        state.is_performing_action = True  # Simulation in progress
        state.last_activity_time = time.time() - 30
        mock_sim.get_state.return_value = state
        mock_sim.log = Mock()

        old_time = state.last_activity_time
        old_pos = state.initial_mouse_position

        on_mouse_event(500, 600)

        # State should not be updated
        assert state.last_activity_time == old_time
        assert state.initial_mouse_position == old_pos

    @patch('activity_simulator.listeners.simulation')
    def test_mouse_event_after_work(self, mock_sim):
        """Test mouse event after work hours sets flag"""
        from activity_simulator.listeners import on_mouse_event

        state = Mock()
        state.lock = MagicMock()
        state.is_performing_action = False
        state.user_activity_after_work = False
        mock_sim.get_state.return_value = state
        mock_sim.is_after_work.return_value = True
        mock_sim.is_work_hours.return_value = False
        mock_sim.log = Mock()

        on_mouse_event(100, 200)

        # Check that after work flag was set
        assert state.user_activity_after_work is True

    @patch('activity_simulator.listeners.simulation')
    @patch('activity_simulator.listeners.time')
    def test_mouse_event_logging_throttle(self, mock_time, mock_sim):
        """Test mouse event logs only once per second"""
        from activity_simulator.listeners import on_mouse_event

        state = Mock()
        state.lock = MagicMock()
        state.is_performing_action = False
        state.last_mouse_log_time = 0
        mock_sim.get_state.return_value = state
        mock_sim.is_after_work.return_value = False
        mock_sim.is_work_hours.return_value = True
        mock_sim.log = Mock()

        # Mock time to simulate events within 1 second
        mock_time.time.return_value = 1.0

        # Multiple mouse events within 1 second
        on_mouse_event(100, 200)
        on_mouse_event(150, 250)

        # Log should only be called once (throttled)
        assert mock_sim.log.call_count == 1


class TestOnMouseClick:
    """Tests for on_mouse_click()"""

    @patch('activity_simulator.listeners.simulation')
    def test_basic_mouse_click(self, mock_sim):
        """Test basic mouse click updates state"""
        from activity_simulator.listeners import on_mouse_click

        state = Mock()
        state.lock = MagicMock()
        state.is_performing_action = False
        state.last_activity_time = 0
        state.current_idle_threshold = 100
        state.is_simulating = True
        state.absolute_anchor_position = (500, 500)
        mock_sim.get_state.return_value = state
        mock_sim.is_after_work.return_value = False
        mock_sim.is_work_hours.return_value = True
        mock_sim.log = Mock()

        button = Mock()
        on_mouse_click(100, 200, button, pressed=True)

        # Check that state was updated
        assert state.last_activity_time > 0
        assert state.current_idle_threshold is None
        assert state.is_simulating is False
        assert state.absolute_anchor_position is None

    @patch('activity_simulator.listeners.simulation')
    def test_mouse_click_during_simulation(self, mock_sim):
        """Test mouse click during simulation is ignored"""
        from activity_simulator.listeners import on_mouse_click

        state = Mock()
        state.lock = MagicMock()
        state.is_performing_action = True  # Simulation in progress
        state.last_activity_time = time.time() - 30
        mock_sim.get_state.return_value = state
        mock_sim.log = Mock()

        old_time = state.last_activity_time
        button = Mock()

        on_mouse_click(500, 600, button, pressed=True)

        # State should not be updated
        assert state.last_activity_time == old_time
        mock_sim.log.assert_called_once()

    @patch('activity_simulator.listeners.simulation')
    def test_mouse_click_release(self, mock_sim):
        """Test mouse click release is ignored"""
        from activity_simulator.listeners import on_mouse_click

        state = Mock()
        state.lock = MagicMock()
        state.is_performing_action = False
        state.last_activity_time = 0
        mock_sim.get_state.return_value = state
        mock_sim.log = Mock()

        button = Mock()
        on_mouse_click(100, 200, button, pressed=False)

        # State should not be updated on release
        assert state.last_activity_time == 0
        mock_sim.log.assert_not_called()

    @patch('activity_simulator.listeners.simulation')
    def test_mouse_click_after_work(self, mock_sim):
        """Test mouse click after work hours sets flag"""
        from activity_simulator.listeners import on_mouse_click

        state = Mock()
        state.lock = MagicMock()
        state.is_performing_action = False
        state.user_activity_after_work = False
        mock_sim.get_state.return_value = state
        mock_sim.is_after_work.return_value = True
        mock_sim.is_work_hours.return_value = False
        mock_sim.log = Mock()

        button = Mock()
        on_mouse_click(100, 200, button, pressed=True)

        # Check that after work flag was set
        assert state.user_activity_after_work is True


class TestCheckAndUpdateActivityAfterWork:
    """Tests for _check_and_update_activity_after_work()"""

    @patch('activity_simulator.listeners.simulation')
    def test_during_work_hours(self, mock_sim):
        """Test returns False during work hours"""
        from activity_simulator.listeners import _check_and_update_activity_after_work

        state = Mock()
        state.config = {'exit_on_activity_after_work': True}
        state.user_activity_after_work = False
        mock_sim.get_state.return_value = state
        mock_sim.is_after_work.return_value = False
        mock_sim.is_work_hours.return_value = True
        mock_sim.log = Mock()

        result = _check_and_update_activity_after_work()

        # Should return False (not after work)
        assert result is False
        assert state.user_activity_after_work is False

    @patch('activity_simulator.listeners.simulation')
    def test_after_work_with_activity(self, mock_sim):
        """Test sets flag and returns True after work with activity"""
        from activity_simulator.listeners import _check_and_update_activity_after_work

        state = Mock()
        state.config = {'exit_on_activity_after_work': True}
        state.user_activity_after_work = False
        mock_sim.get_state.return_value = state
        mock_sim.is_after_work.return_value = True
        mock_sim.is_work_hours.return_value = False
        mock_sim.log = Mock()

        result = _check_and_update_activity_after_work()

        # Should return True and set flag
        assert result is True
        assert state.user_activity_after_work is True
        mock_sim.log.assert_called_once()

    @patch('activity_simulator.listeners.simulation')
    def test_after_work_flag_already_set(self, mock_sim):
        """Test flag already set remains set"""
        from activity_simulator.listeners import _check_and_update_activity_after_work

        state = Mock()
        state.config = {'exit_on_activity_after_work': True}
        state.user_activity_after_work = True  # Already set
        mock_sim.get_state.return_value = state
        mock_sim.is_after_work.return_value = True
        mock_sim.is_work_hours.return_value = False
        mock_sim.log = Mock()

        result = _check_and_update_activity_after_work()

        # Should return True but not log again
        assert result is True
        assert state.user_activity_after_work is True
        mock_sim.log.assert_not_called()

    @patch('activity_simulator.listeners.simulation')
    def test_exit_on_activity_disabled(self, mock_sim):
        """Test returns False when exit_on_activity_after_work is False"""
        from activity_simulator.listeners import _check_and_update_activity_after_work

        state = Mock()
        state.config = {'exit_on_activity_after_work': False}
        state.user_activity_after_work = False
        mock_sim.get_state.return_value = state
        mock_sim.is_after_work.return_value = True
        mock_sim.is_work_hours.return_value = False
        mock_sim.log = Mock()

        result = _check_and_update_activity_after_work()

        # Should return False (exit disabled)
        assert result is False
        assert state.user_activity_after_work is False
        mock_sim.log.assert_not_called()
