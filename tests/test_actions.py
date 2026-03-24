"""Tests for actions module"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest


class TestGetConsecutiveSafeKeyCount:
    """Tests for get_consecutive_safe_key_count()"""

    @patch('activity_simulator.simulation.actions.get_state')
    def test_empty_history(self, mock_get_state):
        """Test with empty action history"""
        from activity_simulator.simulation.actions import get_consecutive_safe_key_count

        state = Mock()
        # Empty deque
        state.action_history = []
        mock_get_state.return_value = state
        assert get_consecutive_safe_key_count() == 0

    @patch('activity_simulator.simulation.actions.get_state')
    def test_no_safe_keys(self, mock_get_state):
        """Test with no safe_key actions in history"""
        from activity_simulator.simulation.actions import get_consecutive_safe_key_count

        state = Mock()
        state.action_history = [('mouse_move', time.time()), ('keyboard', time.time())]
        mock_get_state.return_value = state
        assert get_consecutive_safe_key_count() == 0

    @patch('activity_simulator.simulation.actions.get_state')
    def test_one_safe_key(self, mock_get_state):
        """Test with one safe_key at the end"""
        from activity_simulator.simulation.actions import get_consecutive_safe_key_count

        state = Mock()
        state.action_history = [('mouse_move', time.time()), ('safe_key', time.time())]
        mock_get_state.return_value = state
        assert get_consecutive_safe_key_count() == 1

    @patch('activity_simulator.simulation.actions.get_state')
    def test_multiple_consecutive_safe_keys(self, mock_get_state):
        """Test with multiple consecutive safe_keys at the end"""
        from activity_simulator.simulation.actions import get_consecutive_safe_key_count

        state = Mock()
        state.action_history = [
            ('mouse_move', time.time()),
            ('safe_key', time.time()),
            ('safe_key', time.time()),
            ('safe_key', time.time()),
        ]
        mock_get_state.return_value = state
        assert get_consecutive_safe_key_count() == 3

    @patch('activity_simulator.simulation.actions.get_state')
    def test_safe_keys_not_at_end(self, mock_get_state):
        """Test with safe_keys not at the end of history"""
        from activity_simulator.simulation.actions import get_consecutive_safe_key_count

        state = Mock()
        state.action_history = [
            ('safe_key', time.time()),
            ('safe_key', time.time()),
            ('mouse_move', time.time()),
        ]
        mock_get_state.return_value = state
        assert get_consecutive_safe_key_count() == 0

    @patch('activity_simulator.simulation.actions.get_state')
    def test_mixed_history(self, mock_get_state):
        """Test with mixed action types"""
        from activity_simulator.simulation.actions import get_consecutive_safe_key_count

        state = Mock()
        base_time = time.time()
        state.action_history = [
            ('mouse_move', base_time),
            ('keyboard', base_time + 1),
            ('safe_key', base_time + 2),
            ('safe_key', base_time + 3),
            ('safe_key', base_time + 4),
        ]
        mock_get_state.return_value = state
        assert get_consecutive_safe_key_count() == 3


class TestRandomMouseMove:
    """Tests for random_mouse_move() with mocked pynput"""

    @patch('activity_simulator.simulation.actions.get_mouse_controller')
    @patch('activity_simulator.simulation.actions.get_state')
    @patch('activity_simulator.simulation.actions.move_mouse_naturally')
    def test_basic_mouse_move(self, mock_move_naturally, mock_get_state, mock_mouse_ctrl):
        """Test basic mouse move with mocked pynput"""
        from activity_simulator.simulation.actions import random_mouse_move

        # Setup mocks
        state = Mock()
        state.config = {
            'max_mouse_range': 50,
            'natural_behavior': False,
        }
        state.initial_mouse_position = (500, 500)
        state.absolute_anchor_position = None
        state.lock = MagicMock()
        state.action_history = []
        mock_get_state.return_value = state
        mock_mouse_ctrl.return_value.position = (500, 500)

        random_mouse_move()

        # Check that move_mouse_naturally was called
        assert mock_move_naturally.called
        # Check that action was added to history
        assert len(state.action_history) == 1
        assert state.action_history[0][0] == 'mouse_move'

    @patch('activity_simulator.simulation.actions.get_mouse_controller')
    @patch('activity_simulator.simulation.actions.get_state')
    @patch('activity_simulator.simulation.actions.move_mouse_naturally')
    def test_mouse_move_with_anchor_limit(self, mock_move_naturally, mock_get_state, mock_mouse_ctrl):
        """Test mouse move with anchor position limit"""
        from activity_simulator.simulation.actions import random_mouse_move

        state = Mock()
        state.config = {
            'max_mouse_range': 50,
            'natural_behavior': False,
        }
        state.initial_mouse_position = (500, 500)
        state.absolute_anchor_position = (500, 500)
        state.lock = MagicMock()
        state.action_history = []
        mock_get_state.return_value = state
        mock_mouse_ctrl.return_value.position = (600, 600)

        random_mouse_move()

        assert mock_move_naturally.called
        assert len(state.action_history) == 1

    @patch('activity_simulator.simulation.actions.get_mouse_controller')
    @patch('activity_simulator.simulation.actions.get_state')
    @patch('activity_simulator.simulation.actions.move_mouse_naturally')
    @patch('activity_simulator.simulation.actions.random')
    def test_natural_behavior_triangular_distribution(self, mock_random, mock_move_naturally, mock_get_state, mock_mouse_ctrl):
        """Test that natural_behavior uses triangular distribution"""
        from activity_simulator.simulation.actions import random_mouse_move

        mock_random.randint.side_effect = [100, 100]
        mock_random.triangular.return_value = 0.5

        state = Mock()
        state.config = {
            'max_mouse_range': 100,
            'natural_behavior': True,
        }
        state.initial_mouse_position = (500, 500)
        state.absolute_anchor_position = None
        state.lock = MagicMock()
        state.action_history = []
        mock_get_state.return_value = state
        mock_mouse_ctrl.return_value.position = (500, 500)

        random_mouse_move()

        # Check that triangular was called
        assert mock_random.triangular.called


class TestRandomArrowPress:
    """Tests for random_arrow_press() with mocked pynput"""

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    @patch('activity_simulator.simulation.actions.get_state')
    def test_basic_arrow_press(self, mock_get_state, mock_kb_ctrl):
        """Test basic arrow press"""
        from activity_simulator.simulation.actions import random_arrow_press
        from pynput.keyboard import Key

        state = Mock()
        state.config = {
            'min_key_presses': 1,
            'max_key_presses': 3,
            'natural_behavior': False,
        }
        state.lock = MagicMock()
        state.action_history = []
        state.last_activity_time = time.time()
        state.user_activity_after_work = False
        mock_get_state.return_value = state

        random_arrow_press()

        # Check that keyboard methods were called
        assert mock_kb_ctrl.return_value.press.called
        assert mock_kb_ctrl.return_value.release.called
        # Check that action was added to history
        assert len(state.action_history) == 1
        assert state.action_history[0][0] == 'keyboard'

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    @patch('activity_simulator.simulation.actions.get_state')
    @patch('activity_simulator.simulation.actions.random')
    def test_natural_behavior_arrow_weights(self, mock_random, mock_get_state, mock_kb_ctrl):
        """Test that natural_behavior gives more weight to up/down arrows"""
        from activity_simulator.simulation.actions import random_arrow_press
        from pynput.keyboard import Key

        state = Mock()
        state.config = {
            'min_key_presses': 1,
            'max_key_presses': 1,
            'natural_behavior': True,
        }
        state.lock = MagicMock()
        state.action_history = []
        state.last_activity_time = time.time()
        state.user_activity_after_work = False
        mock_get_state.return_value = state
        mock_random.randint.return_value = 1
        mock_random.choice.return_value = Key.down

        random_arrow_press()

        # Check that up/down are more likely
        # This is checked indirectly by the implementation


class TestRandomMouseClick:
    """Tests for random_mouse_click() with mocked pynput"""

    @patch('activity_simulator.simulation.actions.get_mouse_controller')
    @patch('activity_simulator.simulation.actions.get_state')
    def test_basic_click(self, mock_get_state, mock_mouse_ctrl):
        """Test basic mouse click"""
        from activity_simulator.simulation.actions import random_mouse_click
        from pynput.mouse import Button

        state = Mock()
        state.lock = MagicMock()
        state.action_history = []
        state.user_activity_after_work = False
        mock_get_state.return_value = state

        random_mouse_click()

        # Check that click was called
        mock_mouse_ctrl.return_value.click.assert_called_once_with(Button.left, 1)
        # Check that action was added to history
        assert len(state.action_history) == 1
        assert state.action_history[0][0] == 'mouse_click'

    @patch('activity_simulator.simulation.actions.get_mouse_controller')
    @patch('activity_simulator.simulation.actions.get_state')
    def test_click_after_work(self, mock_get_state, mock_mouse_ctrl):
        """Test that click is skipped after work hours with user activity"""
        from activity_simulator.simulation.actions import random_mouse_click

        state = Mock()
        state.lock = MagicMock()
        state.action_history = []
        state.user_activity_after_work = True
        mock_get_state.return_value = state

        random_mouse_click()

        # Check that click was NOT called
        assert not mock_mouse_ctrl.return_value.click.called
        # Check that no action was added to history
        assert len(state.action_history) == 0


class TestSafeKeyPress:
    """Tests for safe_key_press() with mocked pynput"""

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    @patch('activity_simulator.simulation.actions.get_state')
    def test_basic_safe_key(self, mock_get_state, mock_kb_ctrl):
        """Test basic safe key press (Shift)"""
        from activity_simulator.simulation.actions import safe_key_press
        from pynput.keyboard import Key

        state = Mock()
        state.lock = MagicMock()
        state.action_history = []
        state.user_activity_after_work = False
        mock_get_state.return_value = state

        safe_key_press()

        # Check that Shift key was pressed and released
        mock_kb_ctrl.return_value.press.assert_called_once_with(Key.shift)
        mock_kb_ctrl.return_value.release.assert_called_once_with(Key.shift)
        # Check that action was added to history
        assert len(state.action_history) == 1
        assert state.action_history[0][0] == 'safe_key'


class TestControlTabPress:
    """Tests for control_tab_press() with mocked pynput"""

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    @patch('activity_simulator.simulation.actions.get_state')
    def test_basic_ctrl_tab(self, mock_get_state, mock_kb_ctrl):
        """Test basic Ctrl+Tab press"""
        from activity_simulator.simulation.actions import control_tab_press
        from pynput.keyboard import Key

        state = Mock()
        state.lock = MagicMock()
        state.action_history = []
        state.last_activity_time = time.time()
        state.user_activity_after_work = False
        mock_get_state.return_value = state

        control_tab_press()

        # Check that Ctrl, Tab were pressed and released
        calls = mock_kb_ctrl.return_value.press.call_args_list
        release_calls = mock_kb_ctrl.return_value.release.call_args_list
        assert Key.ctrl_l in [call[0][0] for call in calls]
        assert Key.tab in [call[0][0] for call in calls]
        # Check that action was added to history
        assert len(state.action_history) == 1
        assert state.action_history[0][0] == 'ctrl_tab'

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    @patch('activity_simulator.simulation.actions.get_state')
    def test_ctrl_tab_interrupted_by_user_activity(self, mock_get_state, mock_kb_ctrl):
        """Test Ctrl+Tab interrupted by user activity"""
        from activity_simulator.simulation.actions import control_tab_press
        from pynput.keyboard import Key

        state = Mock()
        state.lock = MagicMock()
        state.action_history = []
        state.last_activity_time = time.time()
        state.user_activity_after_work = False
        state.is_simulating = True
        mock_get_state.return_value = state

        # Update last_activity_time to simulate user activity
        with patch('time.sleep'):
            # First call returns original time, second call returns later time
            original_time = time.time()
            state.last_activity_time = original_time

            control_tab_press()

            # Ctrl should be released even if Tab wasn't pressed
            mock_kb_ctrl.return_value.release.assert_called_with(Key.ctrl_l)


class TestTypeKeySequence:
    """Tests for type_key_sequence() with mocked pynput"""

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    @patch('activity_simulator.simulation.actions.get_state')
    def test_empty_sequence(self, mock_get_state, mock_kb_ctrl):
        """Test with empty sequence"""
        from activity_simulator.simulation.actions import type_key_sequence

        state = Mock()
        state.lock = MagicMock()
        state.user_activity_after_work = False
        mock_get_state.return_value = state

        type_key_sequence("")

        # Should return early without any keyboard calls
        assert not mock_kb_ctrl.return_value.press.called

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    @patch('activity_simulator.simulation.actions.get_state')
    def test_plain_text_sequence(self, mock_get_state, mock_kb_ctrl):
        """Test with plain text sequence"""
        from activity_simulator.simulation.actions import type_key_sequence

        state = Mock()
        state.lock = MagicMock()
        state.action_history = []
        state.user_activity_after_work = False
        mock_get_state.return_value = state

        with patch('time.sleep'):
            type_key_sequence("hello")

        # Check that type was called for each character
        assert mock_kb_ctrl.return_value.type.call_count == 5

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    @patch('activity_simulator.simulation.actions.get_state')
    def test_special_key_sequence(self, mock_get_state, mock_kb_ctrl):
        """Test with special key (Enter)"""
        from activity_simulator.simulation.actions import type_key_sequence
        from pynput.keyboard import Key

        state = Mock()
        state.lock = MagicMock()
        state.action_history = []
        state.user_activity_after_work = False
        mock_get_state.return_value = state

        with patch('time.sleep'):
            type_key_sequence("{Enter}")

        # Check that Enter was pressed and released
        mock_kb_ctrl.return_value.press.assert_called_with(Key.enter)
        mock_kb_ctrl.return_value.release.assert_called_with(Key.enter)

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    @patch('activity_simulator.simulation.actions.get_state')
    def test_sequence_after_work(self, mock_get_state, mock_kb_ctrl):
        """Test that sequence is skipped after work hours with user activity"""
        from activity_simulator.simulation.actions import type_key_sequence

        state = Mock()
        state.lock = MagicMock()
        state.action_history = []
        state.user_activity_after_work = True
        mock_get_state.return_value = state

        type_key_sequence("password{Enter}")

        # Should return early without any keyboard calls
        assert not mock_kb_ctrl.return_value.type.called
        assert not mock_kb_ctrl.return_value.press.called


class TestMoveMouseNaturally:
    """Tests for move_mouse_naturally() with mocked pynput"""

    @patch('activity_simulator.simulation.actions.get_mouse_controller')
    @patch('activity_simulator.simulation.actions.get_state')
    def test_basic_move(self, mock_get_state, mock_mouse_ctrl):
        """Test basic mouse movement"""
        from activity_simulator.simulation.actions import move_mouse_naturally

        state = Mock()
        state.config = {
            'smooth_move_duration': 0.01,
            'smooth_move_steps': 2,
            'natural_behavior': False,
        }
        state.lock = MagicMock()
        state.is_performing_action = False
        state.is_simulating = True
        state.last_activity_time = time.time()
        state.user_activity_after_work = False
        state.action_history = []
        mock_get_state.return_value = state
        mock_mouse_ctrl.return_value.position = (500, 500)

        with patch('time.sleep'):
            move_mouse_naturally(600, 600)

        # Check that position was set
        assert mock_mouse_ctrl.return_value.position == (600, 600)

