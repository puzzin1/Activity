"""Tests for config merging and key management"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest


class TestConfigMerge:
    """Tests for configuration merging"""

    def test_ensure_config_keys_adds_missing(self):
        """Test that missing keys are added from defaults"""
        from activity_simulator import config

        # Minimal config with only some keys
        minimal = {'min_idle_time': 20}

        result = config.ensure_config_keys(minimal)

        # All default keys should be present
        for key in config.DEFAULT_CONFIG:
            assert key in result

    def test_ensure_config_keys_preserves_existing(self):
        """Test that existing keys are not overwritten"""
        from activity_simulator import config

        custom = {
            'min_idle_time': 15,
            'max_idle_time': 100,
            'use_mouse_move': False,
        }

        result = config.ensure_config_keys(custom)

        # Custom values preserved
        assert result['min_idle_time'] == 15
        assert result['max_idle_time'] == 100
        assert result['use_mouse_move'] is False

    def test_ensure_config_keys_returns_dict(self):
        """Test that function returns a dictionary"""
        from activity_simulator import config

        result = config.ensure_config_keys({})

        assert isinstance(result, dict)


class TestDefaultConfig:
    """Tests for DEFAULT_CONFIG"""

    def test_default_config_has_required_keys(self):
        """Test that DEFAULT_CONFIG has all required keys"""
        from activity_simulator import config

        required_keys = [
            'min_idle_time',
            'max_idle_time',
            'min_action_interval',
            'max_action_interval',
            'max_mouse_range',
            'afterhours_mode',
            'work_start_min',
            'work_start_max',
            'work_end_min',
            'work_end_max',
            'lunch_start_min',
            'lunch_end_max',
        ]

        for key in required_keys:
            assert key in config.DEFAULT_CONFIG, f"Missing key: {key}"

    def test_default_config_values_are_valid(self):
        """Test that default config values are sensible"""
        from activity_simulator import config

        cfg = config.DEFAULT_CONFIG

        # Time values should be positive
        assert cfg['min_idle_time'] > 0
        assert cfg['max_idle_time'] > 0
        assert cfg['min_action_interval'] > 0
        assert cfg['max_action_interval'] > 0

        # Min should be less than or equal to max
        assert cfg['min_idle_time'] <= cfg['max_idle_time']
        assert cfg['min_action_interval'] <= cfg['max_action_interval']
        assert cfg['lunch_duration_min'] <= cfg['lunch_duration_max']
        assert cfg['total_break_min'] <= cfg['total_break_max']
