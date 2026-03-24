"""Integration tests to verify all imports and function calls work correctly"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestModuleImports:
    """Test that all modules can be imported and their functions are callable"""

    def test_simulation_module_imports(self):
        """Test that simulation module imports work correctly"""
        # Импортировать весь модуль
        from activity_simulator.simulation import simulation

        # Проверить, что все используемые константы импортированы
        assert hasattr(simulation, 'MAX_CONSECUTIVE_SAFE_KEYS'), \
            "MAX_CONSECUTIVE_SAFE_KEYS not imported in simulation module"

    def test_all_public_functions_callable(self):
        """Test that all publicly exported functions can be imported"""
        # Главные функции симуляции
        from activity_simulator.simulation import (
            simulate_activity,
            show_stats,
            init_simulation,
        )

        # Функции проверки времени
        from activity_simulator.simulation.time_checks import (
            is_work_hours,
            is_before_work,
            is_after_work,
            is_break_time,
            is_after_lunch,
            should_simulate_afterhours,
        )

        # Функции выполнения действий
        from activity_simulator.simulation.actions import (
            random_mouse_move,
            random_arrow_press,
            random_mouse_click,
            safe_key_press,
            control_tab_press,
            type_key_sequence,
            show_shutdown_warning,
        )

        # Обработчики режимов
        from activity_simulator.simulation.modes import execute_burst_activity

        # Убедимся, что все это вызываемые объекты
        assert callable(simulate_activity)
        assert callable(show_stats)
        assert callable(init_simulation)
        assert callable(is_work_hours)
        assert callable(is_break_time)
        assert callable(should_simulate_afterhours)
        assert callable(random_mouse_move)
        assert callable(safe_key_press)
        assert callable(execute_burst_activity)

    def test_constants_defined(self):
        """Test that all required constants are defined"""
        from activity_simulator.simulation.state import (
            MINIMUM_DELAY_AFTER_USER_ACTIVITY,
            MAX_CONSECUTIVE_SAFE_KEYS,
        )

        assert isinstance(MINIMUM_DELAY_AFTER_USER_ACTIVITY, int)
        assert isinstance(MAX_CONSECUTIVE_SAFE_KEYS, int)
        assert MINIMUM_DELAY_AFTER_USER_ACTIVITY > 0
        assert MAX_CONSECUTIVE_SAFE_KEYS > 0
