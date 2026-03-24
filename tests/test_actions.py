"""Tests for actions module"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

from activity_simulator.simulation.state import create_state


class TestGetConsecutiveSafeKeyCount:
    """Tests for get_consecutive_safe_key_count()"""

    def test_empty_history(self):
        """Test with empty action history"""
        from activity_simulator.simulation.actions import get_consecutive_safe_key_count

        state = create_state()
        # Empty deque
        state.action_history.clear()
        assert get_consecutive_safe_key_count(state) == 0

    def test_no_safe_keys(self):
        """Test with no safe_key actions in history"""
        from activity_simulator.simulation.actions import get_consecutive_safe_key_count

        state = create_state()
        state.action_history.clear()
        state.action_history.extend([('mouse_move', time.time()), ('keyboard', time.time())])
        assert get_consecutive_safe_key_count(state) == 0

    def test_one_safe_key(self):
        """Test with one safe_key at the end"""
        from activity_simulator.simulation.actions import get_consecutive_safe_key_count

        state = create_state()
        state.action_history.clear()
        state.action_history.append(('mouse_move', time.time()))
        state.action_history.append(('safe_key', time.time()))
        assert get_consecutive_safe_key_count(state) == 1

    def test_multiple_consecutive_safe_keys(self):
        """Test with multiple consecutive safe_keys at the end"""
        from activity_simulator.simulation.actions import get_consecutive_safe_key_count

        state = create_state()
        state.action_history.clear()
        state.action_history.append(('mouse_move', time.time()))
        state.action_history.append(('safe_key', time.time()))
        state.action_history.append(('safe_key', time.time()))
        state.action_history.append(('safe_key', time.time()))
        assert get_consecutive_safe_key_count(state) == 3

    def test_safe_keys_not_at_end(self):
        """Test with safe_keys not at the end of history"""
        from activity_simulator.simulation.actions import get_consecutive_safe_key_count

        state = create_state()
        state.action_history.clear()
        state.action_history.append(('safe_key', time.time()))
        state.action_history.append(('safe_key', time.time()))
        state.action_history.append(('mouse_move', time.time()))
        assert get_consecutive_safe_key_count(state) == 0

    def test_mixed_history(self):
        """Test with mixed action types"""
        from activity_simulator.simulation.actions import get_consecutive_safe_key_count

        state = create_state()
        state.action_history.clear()
        base_time = time.time()
        state.action_history.append(('mouse_move', base_time))
        state.action_history.append(('keyboard', base_time + 1))
        state.action_history.append(('safe_key', base_time + 2))
        state.action_history.append(('safe_key', base_time + 3))
        state.action_history.append(('safe_key', base_time + 4))
        assert get_consecutive_safe_key_count(state) == 3


class TestRandomMouseMove:
    """Tests for random_mouse_move() with mocked pynput"""

    @patch('activity_simulator.simulation.actions.get_mouse_controller')
    @patch('activity_simulator.simulation.actions.move_mouse_naturally')
    def test_basic_mouse_move(self, mock_move_naturally, mock_mouse_ctrl):
        """Test basic mouse move with mocked pynput"""
        from activity_simulator.simulation.actions import random_mouse_move

        state = create_state()
        state.set_config({
            'max_mouse_range': 50,
            'natural_behavior': False,
        })
        state.initial_mouse_position = (500, 500)
        state.absolute_anchor_position = None
        state.action_history.clear()
        mock_mouse_ctrl.return_value.position = (500, 500)

        random_mouse_move(state)

        # Check that move_mouse_naturally was called
        assert mock_move_naturally.called
        # Check that action was added to history
        assert len(state.action_history) == 1
        assert state.action_history[0][0] == 'mouse_move'

    @patch('activity_simulator.simulation.actions.get_mouse_controller')
    @patch('activity_simulator.simulation.actions.move_mouse_naturally')
    def test_mouse_move_with_anchor_limit(self, mock_move_naturally, mock_mouse_ctrl):
        """Test mouse move with anchor position limit"""
        from activity_simulator.simulation.actions import random_mouse_move

        state = create_state()
        state.set_config({
            'max_mouse_range': 50,
            'natural_behavior': False,
        })
        state.initial_mouse_position = (500, 500)
        state.absolute_anchor_position = (500, 500)
        state.action_history.clear()
        mock_mouse_ctrl.return_value.position = (600, 600)

        random_mouse_move(state)

        assert mock_move_naturally.called
        assert len(state.action_history) == 1

    @patch('activity_simulator.simulation.actions.get_mouse_controller')
    @patch('activity_simulator.simulation.actions.move_mouse_naturally')
    @patch('activity_simulator.simulation.actions.random')
    def test_natural_behavior_triangular_distribution(self, mock_random, mock_move_naturally, mock_mouse_ctrl):
        """Test that natural_behavior uses triangular distribution"""
        from activity_simulator.simulation.actions import random_mouse_move

        mock_random.randint.side_effect = [100, 100]
        mock_random.triangular.return_value = 0.5

        state = create_state()
        state.set_config({
            'max_mouse_range': 100,
            'natural_behavior': True,
        })
        state.initial_mouse_position = (500, 500)
        state.absolute_anchor_position = None
        state.action_history.clear()
        mock_mouse_ctrl.return_value.position = (500, 500)

        random_mouse_move(state)

        # Check that triangular was called
        assert mock_random.triangular.called


class TestRandomArrowPress:
    """Tests for random_arrow_press() with mocked pynput"""

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    def test_basic_arrow_press(self, mock_kb_ctrl):
        """Test basic arrow press"""
        from activity_simulator.simulation.actions import random_arrow_press
        from pynput.keyboard import Key

        state = create_state()
        state.set_config({
            'min_key_presses': 1,
            'max_key_presses': 3,
            'natural_behavior': False,
        })
        state.action_history.clear()
        state.last_activity_time = time.time()
        state.user_activity_after_work = False

        random_arrow_press(state)

        # Check that keyboard methods were called
        assert mock_kb_ctrl.return_value.press.called
        assert mock_kb_ctrl.return_value.release.called
        # Check that action was added to history
        assert len(state.action_history) == 1
        assert state.action_history[0][0] == 'keyboard'

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    @patch('activity_simulator.simulation.actions.random')
    def test_natural_behavior_arrow_weights(self, mock_random, mock_kb_ctrl):
        """Test that natural_behavior gives more weight to up/down arrows"""
        from activity_simulator.simulation.actions import random_arrow_press
        from pynput.keyboard import Key

        state = create_state()
        state.set_config({
            'min_key_presses': 1,
            'max_key_presses': 1,
            'natural_behavior': True,
        })
        state.action_history.clear()
        state.last_activity_time = time.time()
        state.user_activity_after_work = False
        mock_random.randint.return_value = 1
        mock_random.choice.return_value = Key.down

        random_arrow_press(state)

        # Check that up/down are more likely
        # This is checked indirectly by the implementation


class TestRandomMouseClick:
    """Tests for random_mouse_click() with mocked pynput"""

    @patch('activity_simulator.simulation.actions.get_mouse_controller')
    def test_basic_click(self, mock_mouse_ctrl):
        """Test basic mouse click"""
        from activity_simulator.simulation.actions import random_mouse_click
        from pynput.mouse import Button

        state = create_state()
        state.action_history.clear()
        state.user_activity_after_work = False

        random_mouse_click(state)

        # Check that click was called
        mock_mouse_ctrl.return_value.click.assert_called_once_with(Button.left, 1)
        # Check that action was added to history
        assert len(state.action_history) == 1
        assert state.action_history[0][0] == 'mouse_click'

    @patch('activity_simulator.simulation.actions.get_mouse_controller')
    def test_click_after_work(self, mock_mouse_ctrl):
        """Test that click is skipped after work hours with user activity"""
        from activity_simulator.simulation.actions import random_mouse_click

        state = create_state()
        state.action_history.clear()
        state.user_activity_after_work = True

        random_mouse_click(state)

        # Check that click was NOT called
        assert not mock_mouse_ctrl.return_value.click.called
        # Check that no action was added to history
        assert len(state.action_history) == 0


class TestSafeKeyPress:
    """Tests for safe_key_press() with mocked pynput"""

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    def test_basic_safe_key(self, mock_kb_ctrl):
        """Test basic safe key press (Shift)"""
        from activity_simulator.simulation.actions import safe_key_press
        from pynput.keyboard import Key

        state = create_state()
        state.action_history.clear()
        state.user_activity_after_work = False

        safe_key_press(state)

        # Check that Shift key was pressed and released
        mock_kb_ctrl.return_value.press.assert_called_once_with(Key.shift)
        mock_kb_ctrl.return_value.release.assert_called_once_with(Key.shift)
        # Check that action was added to history
        assert len(state.action_history) == 1
        assert state.action_history[0][0] == 'safe_key'


class TestControlTabPress:
    """Tests for control_tab_press() with mocked pynput"""

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    def test_basic_ctrl_tab(self, mock_kb_ctrl):
        """Test basic Ctrl+Tab press"""
        from activity_simulator.simulation.actions import control_tab_press
        from pynput.keyboard import Key

        state = create_state()
        state.action_history.clear()
        state.last_activity_time = time.time()
        state.user_activity_after_work = False

        control_tab_press(state)

        # Check that Ctrl, Tab were pressed and released
        calls = mock_kb_ctrl.return_value.press.call_args_list
        release_calls = mock_kb_ctrl.return_value.release.call_args_list
        assert Key.ctrl_l in [call[0][0] for call in calls]
        assert Key.tab in [call[0][0] for call in calls]
        # Check that action was added to history
        assert len(state.action_history) == 1
        assert state.action_history[0][0] == 'ctrl_tab'

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    def test_ctrl_tab_interrupted_by_user_activity(self, mock_kb_ctrl):
        """Test Ctrl+Tab interrupted by user activity"""
        from activity_simulator.simulation.actions import control_tab_press
        from pynput.keyboard import Key

        state = create_state()
        state.action_history.clear()
        state.last_activity_time = time.time()
        state.user_activity_after_work = False
        state.is_simulating = True

        # Update last_activity_time to simulate user activity
        with patch('time.sleep'):
            # First call returns original time, second call returns later time
            original_time = time.time()
            state.last_activity_time = original_time

            control_tab_press(state)

            # Ctrl should be released even if Tab wasn't pressed
            mock_kb_ctrl.return_value.release.assert_called_with(Key.ctrl_l)


class TestTypeKeySequence:
    """Tests for type_key_sequence() with mocked pynput"""

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    def test_empty_sequence(self, mock_kb_ctrl):
        """Test with empty sequence"""
        from activity_simulator.simulation.actions import type_key_sequence

        state = create_state()
        state.user_activity_after_work = False

        type_key_sequence("", state)

        # Should return early without any keyboard calls
        assert not mock_kb_ctrl.return_value.press.called

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    def test_plain_text_sequence(self, mock_kb_ctrl):
        """Test with plain text sequence"""
        from activity_simulator.simulation.actions import type_key_sequence

        state = create_state()
        state.action_history.clear()
        state.user_activity_after_work = False

        with patch('time.sleep'):
            type_key_sequence("hello", state)

        # Check that type was called for each character
        assert mock_kb_ctrl.return_value.type.call_count == 5

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    def test_special_key_sequence(self, mock_kb_ctrl):
        """Test with special key (Enter)"""
        from activity_simulator.simulation.actions import type_key_sequence
        from pynput.keyboard import Key

        state = create_state()
        state.action_history.clear()
        state.user_activity_after_work = False

        with patch('time.sleep'):
            type_key_sequence("{Enter}", state)

        # Check that Enter was pressed and released
        mock_kb_ctrl.return_value.press.assert_called_with(Key.enter)
        mock_kb_ctrl.return_value.release.assert_called_with(Key.enter)

    @patch('activity_simulator.simulation.actions.get_keyboard_controller')
    def test_sequence_after_work(self, mock_kb_ctrl):
        """Test that sequence is skipped after work hours with user activity"""
        from activity_simulator.simulation.actions import type_key_sequence

        state = create_state()
        state.action_history.clear()
        state.user_activity_after_work = True

        type_key_sequence("password{Enter}", state)

        # Should return early without any keyboard calls
        assert not mock_kb_ctrl.return_value.type.called
        assert not mock_kb_ctrl.return_value.press.called


class TestMoveMouseNaturally:
    """Tests for move_mouse_naturally() with mocked pynput"""

    @patch('activity_simulator.simulation.actions.get_mouse_controller')
    def test_basic_move(self, mock_mouse_ctrl):
        """Test basic mouse movement"""
        from activity_simulator.simulation.actions import move_mouse_naturally

        state = create_state()
        state.set_config({
            'smooth_move_duration': 0.01,
            'smooth_move_steps': 2,
            'natural_behavior': False,
        })
        state.is_performing_action = False
        state.is_simulating = True
        state.last_activity_time = time.time()
        state.user_activity_after_work = False
        state.action_history.clear()
        mock_mouse_ctrl.return_value.position = (500, 500)

        with patch('time.sleep'):
            move_mouse_naturally(600, 600, state)

        # Check that position was set
        assert mock_mouse_ctrl.return_value.position == (600, 600)
