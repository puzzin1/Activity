"""
Основная точка входа программы симуляции активности.
Инициализирует компоненты и запускает главный цикл.
"""

from typing import Optional
import time
import os
import sys
import signal
import atexit
from threading import Thread
from pynput import mouse, keyboard
from datetime import datetime

from . import config
from . import simulation
from . import listeners
from . import utils


# === Словари префиксов для разных режимов вывода ===

_PREFIX_CONSOLE = {
    'header': '🚀',
    'config': '📅',
    'tracking': '🖱️ ',
    'schedule': '⏰',
    'params': '⚙️ ',
    'actions': '🎯',
    'afterhours': '🌙',
    'after_lunch': '🍽️',
    'shutdown': '🔌',
    'friday': ' 🎉 ПЯТНИЦА!',
    'before_work': '🌅 Перед работой',
    'after_work': '🌙 После работы',
    'disabled_afterhours': '🚫 Отключен',
    'before_only': '🌅 Только до работы',
    'before_and_after': '🌅🌙 До и после работы',
    'disabled_worktime': '🌙 Внерабочее время - активность отключена',
}

_PREFIX_LOG = {
    'header': '',
    'config': '',
    'tracking': '',
    'schedule': '',
    'params': '',
    'actions': '',
    'afterhours': '',
    'after_lunch': '',
    'shutdown': '',
    'friday': ' (ПЯТНИЦА - короткий день)',
    'before_work': 'Перед работой',
    'after_work': 'После работы',
    'disabled_afterhours': 'Отключен',
    'before_only': 'Только до работы',
    'before_and_after': 'До и после работы',
    'disabled_worktime': 'Внерабочее время - активность отключена',
}

_AFTERHOURS_MODE_DISPLAY = {
    'disabled': ('Отключен', '🚫 Отключен'),
    'before_only': ('Только до работы', '🌅 Только до работы'),
    'before_and_after': ('До и после работы', '🌅🌙 До и после работы'),
}


def _get_prefixes(for_log: bool) -> dict:
    """Возвращает словарь префиксов в зависимости от режима вывода"""
    return _PREFIX_LOG if for_log else _PREFIX_CONSOLE


def _format_header(prefixes: dict, state: 'simulation.SimulationState') -> list[str]:
    """Форматирует заголовок"""
    lines = []
    header_prefix = prefixes['header']
    config_prefix = prefixes['config']
    tracking_prefix = prefixes['tracking']

    lines.append("=" * 70)
    header = f"{header_prefix} ПРОГРАММА СИМУЛЯЦИИ АКТИВНОСТИ ЗАПУЩЕНА"
    if header_prefix:
        lines.append(header)
    else:
        lines.append("ПРОГРАММА СИМУЛЯЦИИ АКТИВНОСТИ ЗАПУЩЕНА")
    lines.append("=" * 70)
    lines.append(f"{config_prefix} Конфигурация: {config.get_config_filename()}")
    lines.append(f"{tracking_prefix} Отслеживание: Мышь + Тачпад + Клавиатура")
    lines.append("")
    return lines


def _format_schedule_info(prefixes: dict, state: 'simulation.SimulationState') -> list[str]:
    """Форматирует информацию о расписании"""
    lines = []
    schedule_prefix = prefixes['schedule']
    friday_indicator = prefixes['friday']

    day_indicator = friday_indicator if state.schedule.get('is_friday', False) else ""
    lines.append(f"{schedule_prefix} РАСПИСАНИЕ НА СЕГОДНЯ:{day_indicator}")

    lunch_duration = utils.time_str_to_minutes(state.schedule['lunch_end']) - utils.time_str_to_minutes(state.schedule['lunch_start'])
    lines.append(f"  • Рабочее время: {state.schedule['work_start']} - {state.schedule['work_end']}")
    lines.append(f"  • Обед: {state.schedule['lunch_start']} - {state.schedule['lunch_end']} ({lunch_duration} мин)")

    if state.schedule['breaks']:
        lines.append(f"  • Перерывы:")
        for i, brk in enumerate(state.schedule['breaks'], 1):
            lines.append(f"    {i}. {brk['start']} - {brk['end']} ({brk['duration']} мин)")
    else:
        lines.append(f"  • Перерывы: нет")

    lines.append("")
    return lines


def _format_params_info(prefixes: dict, state: 'simulation.SimulationState') -> list[str]:
    """Форматирует основные параметры"""
    lines = []
    params_prefix = prefixes['params']

    lines.append(f"{params_prefix} ОСНОВНЫЕ ПАРАМЕТРЫ:")
    lines.append(f"  • Порог бездействия: {state.config['min_idle_time']}-{state.config['max_idle_time']} сек")
    lines.append(f"  • Интервал между действиями: {state.config['min_action_interval']}-{state.config['max_action_interval']} сек")
    lines.append(f"  • Серия нажатий стрелок: {state.config['min_key_presses']}-{state.config['max_key_presses']} раз")
    lines.append(f"  • Макс. диапазон мыши: {state.config['max_mouse_range']} пикс")
    lines.append("")
    return lines


def _format_actions_info(prefixes: dict, state: 'simulation.SimulationState') -> list[str]:
    """Форматирует информацию о типах действий"""
    lines = []
    actions_prefix = prefixes['actions']

    lines.append(f"{actions_prefix} ТИПЫ ДЕЙСТВИЙ:")
    lines.append(f"  • Движение мыши: {'✓' if state.config['use_mouse_move'] else '✗'} (вес: {state.config['action_weight_mouse_move']})")
    lines.append(f"  • Стрелки клавиатуры: {'✓' if state.config['use_keyboard'] else '✗'} (вес: {state.config['action_weight_keyboard']})")
    lines.append(f"  • Ctrl+Tab: {'✓' if state.config['use_keyboard'] else '✗'} (вес: {state.config['action_weight_ctrl_tab']})")
    lines.append(f"  • Клики мыши: {'✓' if state.config['use_mouse_click'] else '✗'} (вес: {state.config['action_weight_mouse_click']})")
    lines.append(f"  • Shift (безопасный): {'✓' if state.config['natural_behavior'] else '✗'} (вес: {state.config['action_weight_safe_key']})")
    lines.append(f"  • Естественное поведение: {'✓' if state.config['natural_behavior'] else '✗'}")
    lines.append("")
    return lines


def _format_afterhours_info(prefixes: dict, state: 'simulation.SimulationState') -> list[str]:
    """Форматирует информацию о внерабочем режиме"""
    lines = []
    afterhours_prefix = prefixes['afterhours']

    mode = state.config['afterhours_mode']
    mode_display = _AFTERHOURS_MODE_DISPLAY.get(mode, (mode, mode))[1 if prefixes.get('friday') == ' 🎉 ПЯТНИЦА!' else 0]
    lines.append(f"{afterhours_prefix} ВНЕРАБОЧИЙ РЕЖИМ: {mode_display}")

    if mode != 'disabled':
        lines.append(f"  • Всплески активности: {state.config['afterhours_burst_duration_min']}-{state.config['afterhours_burst_duration_max']} сек")
        lines.append(f"  • Интервал между всплесками: {state.config['afterhours_burst_interval_min']}-{state.config['afterhours_burst_interval_max']} мин")

    lines.append("")
    return lines


def _format_after_lunch_info(prefixes: dict, state: 'simulation.SimulationState') -> list[str]:
    """Форматирует информацию о действиях после обеда"""
    lines = []
    after_lunch_prefix = prefixes['after_lunch']

    lines.append(f"{after_lunch_prefix} ДЕЙСТВИЯ ПОСЛЕ ОБЕДА:")
    if state.config.get('after_lunch_action', False):
        lines.append(f"  • Переменная окружения: ***")
        lines.append(f"  • Задержка после обеда: {state.config.get('after_lunch_delay', 5)} сек")
    else:
        lines.append(f"  • Ввод последовательности: ✗ (отключено)")
    lines.append("")
    return lines


def _format_shutdown_info(prefixes: dict) -> list[str]:
    """Форматирует информацию о завершении программы"""
    lines = []
    shutdown_prefix = prefixes['shutdown']

    lines.append(f"{shutdown_prefix} ПРИ ЗАВЕРШЕНИИ ПРОГРАММЫ (Ctrl+C):")
    lines.append(f"  • Действие: Просто завершение программы")
    lines.append("=" * 70)
    return lines


def _format_current_status(prefixes: dict, state: 'simulation.SimulationState') -> list[str]:
    """Форматирует текущий статус"""
    lines = []

    if simulation.is_work_hours(state):
        on_break, break_type = simulation.is_break_time(state)
        if on_break:
            lines.append(f"Текущий статус: Перерыв ({break_type})")
        else:
            lines.append(f"Текущий статус: Рабочее время - активность включена")
    else:
        if simulation.should_simulate_afterhours(state):
            if simulation.is_before_work(state):
                time_indicator = prefixes['before_work']
            else:
                time_indicator = prefixes['after_work']
            lines.append(f"{time_indicator} - режим всплесков активности")
        else:
            lines.append(f"{prefixes['disabled_worktime']}")

    lines.append("")
    lines.append("Для остановки нажмите Ctrl+C")
    lines.append("")
    return lines


def _format_log_suffix(state: 'simulation.SimulationState') -> list[str]:
    """Форматирует суффикс для лога (файл лога и позиция мыши)"""
    lines = []
    lines.append(f"Файл лога: {state.log_file_path}")
    lines.append(f"Начальная позиция мыши: {state.initial_mouse_position}")
    lines.append("=" * 70)
    return lines


def format_startup_info(state: 'simulation.SimulationState', for_log: bool = False) -> str:
    """
    Форматирует информацию о запуске для вывода в консоль или лог.

    Args:
        state: Экземпляр состояния симуляции
        for_log: True если форматируется для лога (без emoji)

    Returns:
        Отформатированная строка с информацией о запуске
    """
    prefixes = _get_prefixes(for_log)
    lines = []

    lines.extend(_format_header(prefixes, state))
    lines.extend(_format_schedule_info(prefixes, state))
    lines.extend(_format_params_info(prefixes, state))
    lines.extend(_format_actions_info(prefixes, state))
    lines.extend(_format_afterhours_info(prefixes, state))
    lines.extend(_format_after_lunch_info(prefixes, state))
    lines.extend(_format_shutdown_info(prefixes))
    lines.extend(_format_current_status(prefixes, state))

    if for_log:
        lines.extend(_format_log_suffix(state))

    return "\n".join(lines)


# Глобальные ссылки на слушатели для корректной очистки
_keyboard_listener: Optional[keyboard.Listener] = None
_mouse_listener: Optional[mouse.Listener] = None


def _cleanup_listeners() -> None:
    """Останавливает слушатели pynput при завершении программы"""
    global _keyboard_listener, _mouse_listener

    if _keyboard_listener is not None:
        try:
            _keyboard_listener.stop()
            _keyboard_listener.join(timeout=2.0)
        except Exception:
            pass

    if _mouse_listener is not None:
        try:
            _mouse_listener.stop()
            _mouse_listener.join(timeout=2.0)
        except Exception:
            pass


def _cleanup_resources() -> None:
    """Очищает все ресурсы при завершении программы"""
    simulation.close_logger()
    _cleanup_listeners()


def main() -> None:
    """Основная функция запуска программы"""
    global _keyboard_listener, _mouse_listener

    # Регистрируем обработчик очистки
    atexit.register(_cleanup_resources)

    # Загружаем конфигурацию и инициализируем симуляцию
    cfg, sched = config.load_or_create_config()
    state = simulation.init_simulation(cfg, sched)

    # Генерируем имя лог-файла
    log_filename = datetime.now().strftime('activity_log_%Y%m%d_%H%M%S.txt')

    # Инициализируем логгер (state.log_file_path устанавливается здесь)
    simulation.init_logger(log_filename, enabled=True, verbose=state.config.get('verbose_logging', True), state=state)

    # Ротация лог-файлов (вызывается ПОСЛЕ init_logger, когда state.log_file_path уже установлен)
    simulation.setup_log_rotation(state)

    # Запуск слушателей
    _keyboard_listener = keyboard.Listener(on_press=listeners.on_keyboard_event)
    _mouse_listener = mouse.Listener(on_move=listeners.on_mouse_event,
                                     on_click=listeners.on_mouse_click)

    _keyboard_listener.start()
    _mouse_listener.start()

    state.initial_mouse_position = simulation.get_mouse_controller().position

    # === ВЫВОД ИНФОРМАЦИИ ===
    print(format_startup_info(state, for_log=False))

    # === СОХРАНЕНИЕ ИНФОРМАЦИИ В ЛОГ ===
    if state.config['verbose_logging']:
        for line in format_startup_info(state, for_log=True).split('\n'):
            simulation.log(line, state=state)

    # === ЗАПУСК ПОТОКОВ СИМУЛЯЦИИ ===
    # Запускаем потоки только после вывода всей информации
    simulate_thread = Thread(target=simulation.simulate_activity, daemon=True)
    stats_thread = Thread(target=simulation.show_stats, daemon=True)

    simulate_thread.start()
    stats_thread.start()

    # === ОБРАБОТКА ЗАВЕРШЕНИЯ ===
    # Флаг для корректного завершения
    running = True

    def signal_handler(sig: int, frame: Optional['object']) -> None:
        """Обработчик сигнала Ctrl+C"""
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, signal_handler)

    # Главный цикл - ждем завершения
    try:
        while running:
            time.sleep(0.5)
            # Проверяем, завершилась ли симуляция (через ExitSimulation)
            if state.simulation_finished:
                running = False
    except KeyboardInterrupt:
        pass

    # Обработка завершения - определяем причину
    if state.simulation_finished:
        # Симуляция завершилась сама (через ExitSimulation)
        print("\n\n🏁 Программа завершена автоматически")
    else:
        # Обычное завершение (Ctrl+C или пользователь)
        print("\n\n🛑 Программа остановлена пользователем")

    if state.config['verbose_logging']:
        print(f"📄 Лог сохранён в файл: {state.log_file_path}")
        simulation.log("", state=state)
        simulation.log("=" * 70, state=state)
        simulation.log(f"Программа завершена. Всего действий: {len(state.action_history)}", state=state)
        simulation.log("=" * 70, state=state)

    # При нажатии Ctrl-C программа просто завершается
    print("👋 Программа завершена. До свидания!")
    sys.exit(0)


if __name__ == "__main__":
    main()
