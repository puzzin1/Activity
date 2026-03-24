"""
Пакет симуляции активности.

Содержит модули для симуляции пользовательской активности:
- state: Управление глобальным состоянием симуляции
- logger: Логгер на базе стандартной библиотеки logging
- time_checks: Функции проверки времени
- actions: Функции выполнения действий
- modes: Обработчики режимов
- simulation: Главный цикл симуляции
"""

from .state import (
    ExitSimulation,
    SimulationState,
    create_state,
    get_state,
    MINIMUM_DELAY_AFTER_USER_ACTIVITY,
    MAX_CONSECUTIVE_SAFE_KEYS,
    get_mouse_controller,
    get_keyboard_controller,
)

from .logger import (
    init_logger,
    close_logger,
    log,
    setup_log_rotation,
)

from .time_checks import (
    is_work_hours,
    is_before_work,
    is_after_work,
    is_break_time,
    is_after_lunch,
    should_simulate_afterhours,
)

from .actions import (
    type_key_sequence,
    random_mouse_move,
    random_arrow_press,
    random_mouse_click,
    safe_key_press,
    control_tab_press,
    show_shutdown_warning,
)

from .modes import execute_burst_activity

from .simulation import (
    simulate_activity,
    show_stats,
    init_simulation,
)

__all__ = [
    # Exceptions
    'ExitSimulation',
    # State
    'SimulationState',
    'create_state',
    'get_state',
    'MINIMUM_DELAY_AFTER_USER_ACTIVITY',
    'MAX_CONSECUTIVE_SAFE_KEYS',
    'get_mouse_controller',
    'get_keyboard_controller',
    # Logger
    'init_logger',
    'close_logger',
    'log',
    'setup_log_rotation',
    # Time checks
    'is_work_hours',
    'is_before_work',
    'is_after_work',
    'is_break_time',
    'is_after_lunch',
    'should_simulate_afterhours',
    # Actions
    'type_key_sequence',
    'random_mouse_move',
    'random_arrow_press',
    'random_mouse_click',
    'safe_key_press',
    'control_tab_press',
    'show_shutdown_warning',
    # Modes
    'execute_burst_activity',
    # Simulation
    'simulate_activity',
    'show_stats',
    'init_simulation',
]
