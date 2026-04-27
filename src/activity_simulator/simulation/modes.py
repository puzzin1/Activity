"""
Модуль обработчиков режимов симуляции.

Содержит функции для выполнения активности в разных режимах:
внерабочее время, перерывы.
"""

import random
import time
from typing import Optional, Callable, Tuple

from .state import SimulationState, MINIMUM_DELAY_AFTER_USER_ACTIVITY, MAX_CONSECUTIVE_SAFE_KEYS, get_mouse_controller
from .logger import log
from .actions import get_consecutive_safe_key_count, random_mouse_move, safe_key_press


def execute_burst_activity(
    burst_time_attr: str,
    burst_interval_min: int,
    burst_interval_max: int,
    burst_duration_min: int,
    burst_duration_max: int,
    mode_name: str,
    time_indicator: str = "",
    check_break_ended: Optional[Callable[[], Tuple[bool, Optional[str]]]] = None,
    state: 'SimulationState' = None,
) -> str:
    """
    Универсальная функция выполнения всплеска активности.

    Используется как для внерабочего режима, так и для режима перерывов.

    Args:
        burst_time_attr: Имя атрибута на state (например, 'last_afterhours_burst_time')
        burst_interval_min: Мин. интервал между всплесками в минутах
        burst_interval_max: Макс. интервал между всплесками в минутах
        burst_duration_min: Мин. продолжительность всплеска в секундах
        burst_duration_max: Макс. продолжительность всплеска в секундах
        mode_name: Название режима для логов
        time_indicator: Emoji индикатор
        check_break_ended: Функция для проверки окончания перерыва
        state: Экземпляр состояния симуляции

    Returns:
        str: 'completed', 'interrupted', 'ended', или 'waiting'
    """

    time_since_burst = time.time() - getattr(state, burst_time_attr)
    burst_interval = random.uniform(
        burst_interval_min * 60,
        burst_interval_max * 60
    )

    time_since_user_activity = state.time_since_last_user_activity()

    if time_since_burst >= burst_interval and time_since_user_activity >= MINIMUM_DELAY_AFTER_USER_ACTIVITY:
        burst_duration = random.uniform(burst_duration_min, burst_duration_max)

        log(f"{time_indicator} {mode_name}: всплеск активности на {burst_duration:.0f} сек", state=state)

        burst_end_time = time.time() + burst_duration

        with state.lock:
            mouse_controller = get_mouse_controller()
            state.absolute_anchor_position = mouse_controller.position
            state.initial_mouse_position = mouse_controller.position
            state.is_simulating = True

        burst_interrupted = False
        burst_completed = False

        while time.time() < burst_end_time:
            # Проверяем, не закончился ли перерыв
            if check_break_ended is not None:
                on_break_check, _ = check_break_ended()
                if not on_break_check:
                    log(f"☕ Перерыв завершился. Выход из режима перерыва.", state=state)
                    state.is_simulating = False
                    return 'ended'

            # Проверка активности пользователя после работы
            if state.user_activity_after_work:
                log(f"🚪 {mode_name}: прерывание всплеска из-за активности пользователя после рабочего дня", state=state)
                burst_interrupted = True
                state.is_simulating = False
                break

            # КРИТИЧЕСКОЕ ПРЕРЫВАНИЕ: проверяем активность пользователя перед КАЖДЫМ действием
            time_since_user_activity = state.time_since_last_user_activity()
            if time_since_user_activity < MINIMUM_DELAY_AFTER_USER_ACTIVITY:
                log(f"⚠️ {mode_name}: всплеск прерван активностью пользователя", state=state)
                burst_interrupted = True
                state.is_simulating = False
                break

            _perform_light_action(state)

            time.sleep(random.uniform(2, 5))
        else:
            burst_completed = True

        state.is_simulating = False

        if burst_interrupted:
            return 'interrupted'

        if burst_completed:
            setattr(state, burst_time_attr, time.time())
            log(f"{time_indicator} {mode_name}: всплеск активности завершен. Следующий через {burst_interval/60:.1f} мин", state=state)
            return 'completed'

    else:
        if time_since_user_activity < MINIMUM_DELAY_AFTER_USER_ACTIVITY:
            remaining = MINIMUM_DELAY_AFTER_USER_ACTIVITY - time_since_user_activity
            log(f"⏸️  Ожидание после активности пользователя: {remaining:.1f} сек", 'DEBUG', state=state)
        time.sleep(10)

    return 'waiting'


def _perform_light_action(state: 'SimulationState') -> None:
    """
    Выполняет легкое действие (используется в перерывах и внерабочем режиме).

    Args:
        state: Экземпляр состояния симуляции
    """
    config = state.config

    consecutive_safe_keys = get_consecutive_safe_key_count(state)
    available_actions = []

    if config['use_mouse_move']:
        available_actions.append('mouse_move')

    if consecutive_safe_keys < MAX_CONSECUTIVE_SAFE_KEYS:
        available_actions.append('safe_key')

    if not available_actions:
        available_actions.append('safe_key')

    action = random.choice(available_actions)

    try:
        if action == 'mouse_move':
            random_mouse_move(state)
        elif action == 'safe_key':
            safe_key_press(state)
    except Exception as e:
        log(f"Ошибка при выполнении действия: {e}", 'ERROR', state=state)
