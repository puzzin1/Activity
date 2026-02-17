"""
Пакет симуляции активности - инструмент для имитации пользовательской активности
для предотвращения перехода компьютера в спящий режим и поддержания статуса 'активен'.
"""

__version__ = "1.0.0"
__author__ = "Activity Simulator"
__description__ = "Автоматическая симуляция пользовательской активности"

# Основной экспорт
from .main import main
from .config import load_or_create_config, get_config_filename, DEFAULT_CONFIG
from .simulation import simulate_activity, show_stats
from .listeners import on_keyboard_event, on_mouse_event, on_mouse_click
from .utils import lock_computer, shutdown_computer, parse_key_sequence

__all__ = [
    'main',
    'load_or_create_config',
    'get_config_filename',
    'DEFAULT_CONFIG',
    'simulate_activity',
    'show_stats',
    'on_keyboard_event',
    'on_mouse_event',
    'on_mouse_click',
    'lock_computer',
    'shutdown_computer',
    'parse_key_sequence',
]