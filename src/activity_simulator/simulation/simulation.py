"""
Главный модуль симуляции активности.

Содержит главный цикл симуляции и функцию инициализации.
"""

import time
import random
import os
from datetime import datetime

from .state import SimulationState, MINIMUM_DELAY_AFTER_USER_ACTIVITY, MAX_CONSECUTIVE_SAFE_KEYS, get_mouse_controller, ExitSimulation
from .logger import log
from .time_checks import (
    is_work_hours, is_before_work, is_after_work,
    is_break_time, is_after_lunch, should_simulate_afterhours,
)
from .actions import (
    type_key_sequence, random_mouse_move, random_arrow_press,
    random_mouse_click, safe_key_press, control_tab_press,
    show_shutdown_warning, get_consecutive_safe_key_count,
)
from .modes import execute_burst_activity


def init_simulation(config: dict, schedule: dict) -> 'SimulationState':
    """
    Инициализирует состояние симуляции конфигурацией и расписанием.

    Args:
        config: Конфигурация программы
        schedule: Расписание рабочего дня

    Returns:
        SimulationState: Инициализированное состояние симуляции
    """
    state = SimulationState()
    state.set_config(config)
    state.set_schedule(schedule)
    current_time = time.time()
    state.last_activity_time = current_time  # Инициализируем текущим временем, чтобы избежать огромных значений
    state.program_start_time = current_time
    return state


def simulate_activity(state: 'SimulationState') -> None:
    """Основной цикл симуляции активности"""
    import traceback
    state.last_afterhours_burst_time = time.time()
    state.last_break_burst_time = time.time()

    try:
        while True:
            config = state.config

            # Проверка: прошло ли 60 секунд с момента запуска программы
            # Первое симулированное действие не ранее 60 сек после запуска
            time_since_start = time.time() - state.program_start_time
            if time_since_start < MINIMUM_DELAY_AFTER_USER_ACTIVITY:
                time.sleep(1)
                continue

            # Проверка активности пользователя после работы
            if state.user_activity_after_work:
                log("🚪 Завершение программы из-за активности пользователя после рабочего дня", state=state)
                print("\n" + "=" * 70)
                print("🚪 ОБНАРУЖЕНА АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЯ")
                print("=" * 70)
                print("Программа завершена без блокировки/выключения компьютера")
                if config['verbose_logging']:
                    print(f"📄 Лог сохранён в файл: {state.log_file_path}")
                print("=" * 70)
                time.sleep(1)
                state.simulation_finished = True
                raise ExitSimulation("Активность пользователя после рабочего дня")

            # Проверяем режим работы
            in_work_hours = is_work_hours(state)
            on_break, break_type = is_break_time(state)

            # === ПРОВЕРКА И ВЫПОЛНЕНИЕ ДЕЙСТВИЙ ПОСЛЕ ОБЕДА ===
            if config.get('after_lunch_action', False) and not state.lunch_sequence_executed:
                # Проверяем, прошел ли обед и находимся ли мы после него
                if in_work_hours and is_after_lunch(state) and not on_break:
                    log(f"🍽️ Обеденный перерыв завершен. Ожидание {config.get('after_lunch_delay', 5)} сек...", state=state)
                    time.sleep(config.get('after_lunch_delay', 5))

                    # Вводим последовательность клавиш из переменной окружения
                    env_var_name = config.get('after_lunch_sequence', '')
                    sequence = os.environ.get(env_var_name, '') if env_var_name else ''
                    if sequence:
                        type_key_sequence(sequence, state)
                        state.lunch_sequence_executed = True
                        state.last_activity_time = time.time()
                    else:
                        log(f"⚠️ Последовательность после обеда не задана", 'WARNING', state)
                        state.lunch_sequence_executed = True

            # === РЕЖИМ ВНЕ РАБОЧЕГО ВРЕМЕНИ ===
            if not in_work_hours:
                # Проверяем, нужна ли активность вне рабочего времени
                if not should_simulate_afterhours(state):
                    # Если мы ПОСЛЕ работы и активность отключена - завершаем программу
                    if is_after_work(state):
                        _handle_work_day_finished(state)

                    # Если мы ДО работы - просто ждем
                    if state.is_simulating:
                        state.is_simulating = False
                        log(f"🌙 Внерабочее время. Активность отключена (режим: {config['afterhours_mode']})", state=state)
                    time.sleep(60)
                    continue

                # Режим всплесков активности
                time_indicator = "🌅" if is_before_work(state) else "🌙"
                execute_burst_activity(
                    'last_afterhours_burst_time',
                    config['afterhours_burst_interval_min'],
                    config['afterhours_burst_interval_max'],
                    config['afterhours_burst_duration_min'],
                    config['afterhours_burst_duration_max'],
                    "Внерабочий режим",
                    time_indicator,
                    state=state,
                )
                continue

            # === РЕЖИМ ПЕРЕРЫВА ===
            if on_break:
                if state.is_simulating:
                    state.is_simulating = False
                    log(f"☕ Перерыв ({break_type}). Переход в режим легкой активности.", state=state)

                # Логика всплесков активности во время перерыва
                execute_burst_activity(
                    'last_break_burst_time',
                    config['afterhours_burst_interval_min'],
                    config['afterhours_burst_interval_max'],
                    config['afterhours_burst_duration_min'],
                    config['afterhours_burst_duration_max'],
                    f"Перерыв ({break_type})",
                    "☕",
                    check_break_ended=lambda: is_break_time(state),
                    state=state,
                )
                continue

            # === ОБЫЧНЫЙ РАБОЧИЙ РЕЖИМ ===
            _handle_work_mode(state)
            continue

    except ExitSimulation:
        raise  # Пробрасываем контролируемое завершение
    except Exception as e:
        # Логируем неперехваченную ошибку перед падением потока
        tb = traceback.format_exc()
        try:
            log(f"КРИТИЧЕСКАЯ ОШИБКА в потоке симуляции: {e}\n{tb}", 'ERROR', state)
        except Exception:
            pass  # Если логгер тоже упал — хотя бы в консоль
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА в потоке симуляции: {e}\n{tb}", file=__import__('sys').stderr)
        raise


def _handle_work_day_finished(state: 'SimulationState') -> None:
    """
    Обрабатывает завершение рабочего дня.

    Args:
        state: Экземпляр состояния симуляции
    """
    config = state.config

    # Если обнаружена активность пользователя — тихо завершаем без предупреждения
    if state.user_activity_after_work:
        log("🚪 Обнаружена активность пользователя после рабочего дня. Завершение программы.", state=state)
        state.simulation_finished = True
        raise ExitSimulation("Активность пользователя после рабочего дня", show_warning=False)

    log(f"🏁 Рабочий день завершен. Программа останавливается (режим: {config['afterhours_mode']})", state=state)

    # Показываем предупреждение, если включено
    should_proceed = True
    if config.get('show_shutdown_warning', True):
        print(f"\n⏰ Показ предупреждения о завершении работы...")
        log("⏰ Показ предупреждения о завершении работы", state=state)
        should_proceed = show_shutdown_warning(state)

    if not should_proceed or state.shutdown_cancelled:
        log("✋ Завершение работы отменено пользователем", state=state)
        print("\n✋ Завершение работы отменено")
        state.simulation_finished = True
        raise ExitSimulation("Завершение отменено пользователем", show_warning=False)

    print("\n" + "=" * 70)
    print("🏁 РАБОЧИЙ ДЕНЬ ЗАВЕРШЕН")
    print("=" * 70)
    print(f"⏰ Время окончания: {datetime.now().strftime('%H:%M:%S')}")
    if config['verbose_logging']:
        print(f"📄 Лог сохранён в файл: {state.log_file_path}")

    # Логируем статистику в файл
    log(f"Всего выполнено действий: {len(state.action_history)}", state=state)

    # Выключение или блокировка компьютера при АВТОМАТИЧЕСКОМ завершении
    from .. import utils

    if config.get('shutdown_on_exit', False):
        print("🔌 ВЫКЛЮЧЕНИЕ КОМПЬЮТЕРА...")
        time.sleep(1)
        success, message = utils.shutdown_computer()
        log(message, state=state)
    elif config.get('lock_on_exit', True):
        print("🔒 Блокировка компьютера...")
        time.sleep(1)
        success, message = utils.lock_computer()
        log(message, state=state)

    print("=" * 70)
    time.sleep(1)  # Задержка перед завершением
    state.simulation_finished = True
    from .state import ExitSimulation
    raise ExitSimulation("Рабочий день завершен", show_warning=False)



def _handle_work_mode(state: 'SimulationState') -> None:
    """
    Обрабатывает обычный рабочий режим.

    Args:
        state: Экземпляр состояния симуляции
    """
    config = state.config

    current_idle_threshold_local = state.current_idle_threshold
    is_simulating = state.is_simulating

    time_since_last_activity = state.time_since_last_user_activity()

    # Генерация нового порога бездействия
    if current_idle_threshold_local is None:
        # Убеждаемся, что первый порог не меньше времени, которое уже прошло
        new_threshold = random.randint(config['min_idle_time'], config['max_idle_time'])

        # Гарантируем, что порог не меньше MINIMUM_DELAY_AFTER_USER_ACTIVITY
        effective_threshold = float(max(new_threshold, MINIMUM_DELAY_AFTER_USER_ACTIVITY))
        if effective_threshold < time_since_last_activity:
            effective_threshold = time_since_last_activity + 5.0  # Добавляем запас 5 сек

        with state.lock:
            state.current_idle_threshold = effective_threshold
        current_idle_threshold_local = effective_threshold
        log(f"Установлен новый порог бездействия: {effective_threshold} сек", 'DEBUG', state)

    # Синхронизируем локальный флаг с состоянием (активность пользователя могла сбросить is_simulating)
    is_simulating = state.is_simulating

    # КРИТИЧЕСКИ ВАЖНО: Минимальная задержка MINIMUM_DELAY_AFTER_USER_ACTIVITY секунд
    if time_since_last_activity >= MINIMUM_DELAY_AFTER_USER_ACTIVITY and \
       (is_simulating or time_since_last_activity >= current_idle_threshold_local):

        # Начало симуляции
        if not is_simulating:
            with state.lock:
                mouse_controller = get_mouse_controller()
                state.absolute_anchor_position = mouse_controller.position
                state.initial_mouse_position = mouse_controller.position
                state.is_simulating = True
            log(f"💼 Начало симуляции активности (бездействие: {time_since_last_activity:.1f} сек)", state=state)

        # Формирование списка доступных действий с весами
        available_actions = []

        if config['use_mouse_move']:
            available_actions.extend(['mouse_move'] * config['action_weight_mouse_move'])

        if config['use_keyboard']:
            available_actions.extend(['keyboard'] * config['action_weight_keyboard'])
            available_actions.extend(['ctrl_tab'] * config['action_weight_ctrl_tab'])

        if config['use_mouse_click']:
            available_actions.extend(['mouse_click'] * config['action_weight_mouse_click'])

        if config['natural_behavior']:
            available_actions.extend(['safe_key'] * config['action_weight_safe_key'])

        if not available_actions:
            available_actions = ['safe_key']

        # Проверка: избегаем 5 подряд нажатий Shift
        consecutive_safe_keys = get_consecutive_safe_key_count(state)
        if consecutive_safe_keys >= 5 and 'safe_key' in available_actions:
            # Удаляем все 'safe_key' из списка доступных действий
            available_actions = [a for a in available_actions if a != 'safe_key']
            log(f"⚠️ Избегаем 5-го подряд нажатия Shift (уже {consecutive_safe_keys} подряд)", 'DEBUG', state)

        # Если после удаления safe_key список пуст, добавляем обратно одно действие
        if not available_actions:
            available_actions = ['safe_key']
            log(f"⚠️ Нет других доступных действий, оставляем safe_key", 'DEBUG', state)

        # Выбор и выполнение действия
        action = random.choice(available_actions)
        log(f"Выбрано действие: {action}", state=state)

        # КОНТРОЛЬНАЯ ПРОВЕРКА: убедимся, что активность пользователя не началась перед действием
        time_since_last_activity_check = state.time_since_last_user_activity()
        if time_since_last_activity_check < MINIMUM_DELAY_AFTER_USER_ACTIVITY:
            log(f"⚠️ Действие отменено - обнаружена активность пользователя ({time_since_last_activity_check:.1f} сек)", state=state)
            with state.lock:
                state.is_simulating = False
            is_simulating = False
        else:
            try:
                if action == 'mouse_move':
                    random_mouse_move(state)
                elif action == 'keyboard':
                    random_arrow_press(state)
                elif action == 'mouse_click':
                    random_mouse_click(state)
                elif action == 'safe_key':
                    safe_key_press(state)
                elif action == 'ctrl_tab':
                    control_tab_press(state)
            except Exception as e:
                log(f"Ошибка при выполнении действия: {e}", 'ERROR', state)

            # Расчет паузы до следующего действия
            action_interval = random.uniform(
                config['min_action_interval'],
                config['max_action_interval']
            )

            # Случайное увеличение паузы для естественности
            if config['natural_behavior'] and random.random() < 0.15:
                action_interval *= random.uniform(1.5, 2.5)
                log(f"Увеличенная пауза: {action_interval:.1f} сек", 'DEBUG', state)

            log(f"Следующее действие через {action_interval:.1f} сек", 'DEBUG', state)
            time.sleep(action_interval)

    else:
        # Режим ожидания
        if is_simulating:
            if not state.is_simulating:
                log("Симуляция прервана активностью пользователя.", 'INFO', state)

        # Показываем оставшееся время с учетом минимальной задержки
        if time_since_last_activity < MINIMUM_DELAY_AFTER_USER_ACTIVITY:
            remaining = MINIMUM_DELAY_AFTER_USER_ACTIVITY - time_since_last_activity
            log(f"Ожидание после активности пользователя. Осталось: {remaining:.1f} сек", 'DEBUG', state)
        else:
            remaining = current_idle_threshold_local - time_since_last_activity
            log(f"Ожидание бездействия. Осталось: {remaining:.1f} сек", 'DEBUG', state)

        time.sleep(1)


def show_stats(state: 'SimulationState') -> None:
    """
    Периодический вывод статистики выполненных действий.

    Args:
        state: Экземпляр состояния симуляции
    """
    while True:
        time.sleep(300)  # Каждые 5 минут
        if len(state.action_history) > 0:
            recent = [a for a in state.action_history if time.time() - a[1] < 3600]
            log(f"[Статистика] Действий за последний час: {len(recent)}", state=state)
