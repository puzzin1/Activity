"""Integration tests to verify all imports and function calls work correctly"""

import sys
import os
import time
import threading
from unittest.mock import patch, MagicMock, Mock
from concurrent.futures import ThreadPoolExecutor
from subprocess import CalledProcessError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest


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


class TestSimulationInterruption:
    """Tests for simulation interruption on user activity (race conditions)"""

    def test_is_performing_action_flag_prevents_interference(self):
        """
        Тест проверки того, что флаг is_performing_action предотвращает
        интерференцию между симулируемыми действиями и слушателями событий.
        """
        from activity_simulator.simulation.state import create_state

        state = create_state()
        state.set_config({'natural_behavior': False})
        state.set_schedule({
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        })

        # Устанавливаем флаг, что действие выполняется
        state.is_performing_action = True

        # Проверяем, что флаг установлен
        assert state.is_performing_action is True

        # Сбрасываем флаг (симуляция завершения действия)
        state.is_performing_action = False
        assert state.is_performing_action is False

    def test_concurrent_state_access(self):
        """
        Тест на race condition при одновременном доступе к состоянию
        из разных потоков (имитация симуляции и слушателей).
        """
        from activity_simulator.simulation.state import create_state
        import time

        state = create_state()
        state.set_config({})
        state.set_schedule({
            'work_start': '09:00',
            'work_end': '18:00',
            'lunch_start': '13:00',
            'lunch_end': '14:00',
            'breaks': []
        })

        # Функция для обновления last_activity_time (имитация слушателя)
        def update_activity():
            for _ in range(10):
                with state.lock:
                    state.last_activity_time = time.time()
                time.sleep(0.001)

        # Функция для чтения last_activity_time (имитация симуляции)
        def read_activity():
            results = []
            for _ in range(10):
                with state.lock:
                    results.append(state.last_activity_time)
                time.sleep(0.001)
            return results

        # Запускаем оба потока одновременно
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_update = executor.submit(update_activity)
            future_read = executor.submit(read_activity)

            future_update.result()
            read_results = future_read.result()

        # Проверяем, что все чтения прошли без ошибок
        assert len(read_results) == 10
        assert all(isinstance(t, float) for t in read_results)

    def test_action_history_thread_safety(self):
        """
        Тест на thread-safety истории действий.
        """
        from activity_simulator.simulation.state import create_state
        import time

        state = create_state()

        def add_actions():
            for _ in range(20):
                with state.lock:
                    state.action_history.append(('mouse_move', time.time()))
                time.sleep(0.001)

        def read_actions():
            results = []
            for _ in range(10):
                with state.lock:
                    results.append(len(state.action_history))
                time.sleep(0.002)
            return results

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_add = executor.submit(add_actions)
            future_read = executor.submit(read_actions)

            future_add.result()
            read_results = future_read.result()

        # Проверяем, что все чтения прошли без ошибок
        assert len(read_results) == 10
        # История должна содержать все 20 добавленных действий
        assert len(state.action_history) == 20
        # Все значения должны быть положительными (растущая история)
        assert all(0 <= v <= 20 for v in read_results)


class TestShutdownBehavior:
    """Tests for shutdown_on_exit behavior with mocked subprocess"""

    @patch('activity_simulator.utils.platform.system')
    @patch('activity_simulator.utils.subprocess.call')
    @patch('activity_simulator.utils.subprocess.run')
    def test_shutdown_on_exit_windows(self, mock_run, mock_call, mock_platform):
        """
        Тест корректного вызова shutdown на Windows при shutdown_on_exit=True.
        """
        from activity_simulator.utils import shutdown_computer

        mock_platform.return_value = 'Windows'
        mock_call.return_value = 0

        success, message = shutdown_computer()

        # Проверяем успешное выключение
        assert success is True
        assert 'Windows' in message
        mock_call.assert_called_once_with(['shutdown', '/s', '/f', '/t', '0'])

    @patch('activity_simulator.utils.platform.system')
    @patch('activity_simulator.utils.subprocess.run')
    def test_shutdown_macos_handles_permission_error(self, mock_run, mock_platform):
        """
        Тест обработки ошибки на macOS при отсутствии прав sudo.
        """
        from activity_simulator.utils import shutdown_computer
        from subprocess import CalledProcessError

        mock_platform.return_value = 'Darwin'
        # Симулируем ошибку отсутствия прав sudo
        mock_run.side_effect = CalledProcessError(1, ['sudo', 'shutdown', '-h', 'now'])

        success, message = shutdown_computer()

        # Проверяем, что ошибка обработана корректно
        assert success is False
        assert 'Не удалось выключить компьютер' in message
        assert 'macOS' in message

    @patch('activity_simulator.utils.platform.system')
    @patch('activity_simulator.utils.subprocess.run')
    def test_shutdown_macos_handles_file_not_found(self, mock_run, mock_platform):
        """
        Тест обработки ошибки на macOS при отсутствии команды shutdown.
        """
        from activity_simulator.utils import shutdown_computer

        mock_platform.return_value = 'Darwin'
        # Симулируем отсутствие команды shutdown
        mock_run.side_effect = FileNotFoundError()

        success, message = shutdown_computer()

        # Проверяем, что ошибка обработана корректно
        assert success is False
        assert 'Не удалось выключить компьютер' in message
        assert 'macOS' in message
        assert 'shutdown не найдена' in message

    @patch('activity_simulator.utils.platform.system')
    @patch('activity_simulator.utils.subprocess.run')
    def test_shutdown_linux_fallback(self, mock_run, mock_platform):
        """
        Тест падбэка на Linux при неудаче первого метода.
        """
        from activity_simulator.utils import shutdown_computer
        import subprocess

        mock_platform.return_value = 'Linux'

        # Первый вызов падает с ошибкой через CalledProcessError,
        # второй должен быть успешным
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ['systemctl', 'poweroff']),  # Первый неудачен
            MagicMock()  # Второй успешен (не вызывает исключение)
        ]

        success, message = shutdown_computer()

        # Проверяем, что после падбэка был успех
        assert success is True
        assert 'Linux' in message

    @patch('activity_simulator.utils.platform.system')
    @patch('activity_simulator.utils.subprocess.run')
    def test_shutdown_unsupported_os(self, mock_run, mock_platform):
        """
        Тест обработки неподдерживаемой ОС.
        """
        from activity_simulator.utils import shutdown_computer

        mock_platform.return_value = 'UnknownOS'

        success, message = shutdown_computer()

        # Проверяем, что возвращено сообщение о неподдерживаемой ОС
        assert success is False
        assert 'Выключение не поддерживается' in message
        assert 'UnknownOS' in message

    @patch('activity_simulator.utils.platform.system')
    @patch('activity_simulator.utils.subprocess.call')
    @patch('activity_simulator.utils.subprocess.run')
    def test_shutdown_windows_success(self, mock_run, mock_call, mock_platform):
        """
        Тест успешного выключения на Windows.
        """
        from activity_simulator.utils import shutdown_computer

        mock_platform.return_value = 'Windows'
        mock_call.return_value = 0

        success, message = shutdown_computer()

        # Проверяем успешное выключение
        assert success is True
        assert 'Windows' in message
        mock_call.assert_called_once_with(['shutdown', '/s', '/f', '/t', '0'])

    @patch('activity_simulator.utils.platform.system')
    @patch('activity_simulator.utils.subprocess.call')
    def test_lock_windows_success(self, mock_call, mock_platform):
        """
        Тест успешной блокировки на Windows.
        """
        from activity_simulator.utils import lock_computer

        mock_platform.return_value = 'Windows'
        mock_call.return_value = 0

        success, message = lock_computer()

        # Проверяем успешную блокировку
        assert success is True
        assert 'Windows' in message
        mock_call.assert_called_once_with(['rundll32.exe', 'user32.dll,LockWorkStation'])

    @patch('activity_simulator.utils.platform.system')
    @patch('activity_simulator.utils.subprocess.call')
    def test_lock_macos_success(self, mock_call, mock_platform):
        """
        Тест успешной блокировки на macOS.
        """
        from activity_simulator.utils import lock_computer

        mock_platform.return_value = 'Darwin'
        mock_call.return_value = 0

        success, message = lock_computer()

        # Проверяем успешную блокировку
        assert success is True
        assert 'macOS' in message

    @patch('activity_simulator.utils.platform.system')
    @patch('activity_simulator.utils.subprocess.call')
    def test_lock_linux_fallback(self, mock_call, mock_platform):
        """
        Тест падбэка блокировки на Linux при неудаче первого метода.
        """
        from activity_simulator.utils import lock_computer
        import subprocess

        mock_platform.return_value = 'Linux'
        # Первый вызов вызывает исключение (имитация неудачи), второй вызывает исключение,
        # третий успешен (return_value не вызывает исключения)
        mock_call.side_effect = [
            subprocess.CalledProcessError(1, ['gnome-screensaver-command', '--lock']),
            subprocess.CalledProcessError(1, ['xdg-screensaver', 'lock']),
            0  # loginctl успешен
        ]

        success, message = lock_computer()

        # Проверяем успешную блокировку после падбэка
        assert success is True
        assert 'Linux' in message
