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


def format_startup_info(state: 'simulation.SimulationState', for_log: bool = False) -> str:
    """
    Форматирует информацию о запуске для вывода в консоль или лог.

    Args:
        state: Экземпляр состояния симуляции
        for_log: True если форматируется для лога (без emoji)

    Returns:
        Отформатированная строка с информацией о запуске
    """
    lines = []

    if for_log:
        lines.append("=" * 70)
        lines.append("ПРОГРАММА СИМУЛЯЦИИ АКТИВНОСТИ ЗАПУЩЕНА")
        lines.append("=" * 70)
        lines.append(f"Конфигурация: {config.get_config_filename()}")
        lines.append("Отслеживание: Мышь + Тачпад + Клавиатура")
    else:
        lines.append("=" * 70)
        lines.append("🚀 ПРОГРАММА СИМУЛЯЦИИ АКТИВНОСТИ ЗАПУЩЕНА")
        lines.append("=" * 70)
        lines.append(f"📅 Конфигурация: {config.get_config_filename()}")
        lines.append("🖱️  Отслеживание: Мышь + Тачпад + Клавиатура")

    lines.append("")

    # Индикатор пятницы
    day_indicator = " (ПЯТНИЦА - короткий день)" if for_log and state.schedule.get('is_friday', False) else (" 🎉 ПЯТНИЦА!" if state.schedule.get('is_friday', False) else "")

    if for_log:
        lines.append(f"РАСПИСАНИЕ НА СЕГОДНЯ:{day_indicator}")
    else:
        lines.append(f"⏰ РАСПИСАНИЕ НА СЕГОДНЯ:{day_indicator}")

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

    if for_log:
        lines.append("ОСНОВНЫЕ ПАРАМЕТРЫ:")
    else:
        lines.append("⚙️  ОСНОВНЫЕ ПАРАМЕТРЫ:")

    lines.append(f"  • Порог бездействия: {state.config['min_idle_time']}-{state.config['max_idle_time']} сек")
    lines.append(f"  • Интервал между действиями: {state.config['min_action_interval']}-{state.config['max_action_interval']} сек")
    lines.append(f"  • Серия нажатий стрелок: {state.config['min_key_presses']}-{state.config['max_key_presses']} раз")
    lines.append(f"  • Макс. диапазон мыши: {state.config['max_mouse_range']} пикс")

    lines.append("")

    if for_log:
        lines.append("ТИПЫ ДЕЙСТВИЙ:")
    else:
        lines.append("🎯 ТИПЫ ДЕЙСТВИЙ:")

    lines.append(f"  • Движение мыши: {'✓' if state.config['use_mouse_move'] else '✗'} (вес: {state.config['action_weight_mouse_move']})")
    lines.append(f"  • Стрелки клавиатуры: {'✓' if state.config['use_keyboard'] else '✗'} (вес: {state.config['action_weight_keyboard']})")
    lines.append(f"  • Ctrl+Tab: {'✓' if state.config['use_keyboard'] else '✗'} (вес: {state.config['action_weight_ctrl_tab']})")
    lines.append(f"  • Клики мыши: {'✓' if state.config['use_mouse_click'] else '✗'} (вес: {state.config['action_weight_mouse_click']})")
    lines.append(f"  • Shift (безопасный): {'✓' if state.config['natural_behavior'] else '✗'} (вес: {state.config['action_weight_safe_key']})")
    lines.append(f"  • Естественное поведение: {'✓' if state.config['natural_behavior'] else '✗'}")

    lines.append("")

    afterhours_mode_names = {
        'disabled': '🚫 Отключен',
        'before_only': '🌅 Только до работы',
        'before_and_after': '🌅🌙 До и после работы'
    }
    if for_log:
        # Для лога используем более простые обозначения
        afterhours_log_names = {
            'disabled': 'Отключен',
            'before_only': 'Только до работы',
            'before_and_after': 'До и после работы'
        }
        mode_display = afterhours_log_names.get(state.config['afterhours_mode'], state.config['afterhours_mode'])
    else:
        mode_display = afterhours_mode_names.get(state.config['afterhours_mode'], state.config['afterhours_mode'])

    if for_log:
        lines.append(f"ВНЕРАБОЧИЙ РЕЖИМ: {mode_display}")
    else:
        lines.append(f"🌙 ВНЕРАБОЧИЙ РЕЖИМ: {mode_display}")

    if state.config['afterhours_mode'] != 'disabled':
        lines.append(f"  • Всплески активности: {state.config['afterhours_burst_duration_min']}-{state.config['afterhours_burst_duration_max']} сек")
        lines.append(f"  • Интервал между всплесками: {state.config['afterhours_burst_interval_min']}-{state.config['afterhours_burst_interval_max']} мин")

    lines.append("")

    if for_log:
        lines.append("ДЕЙСТВИЯ ПОСЛЕ ОБЕДА:")
    else:
        lines.append("🍽️ ДЕЙСТВИЯ ПОСЛЕ ОБЕДА:")

    if state.config.get('after_lunch_action', False):
        env_var_name = state.config.get('after_lunch_sequence', '')
        if for_log:
            lines.append(f"  • Переменная окружения: {env_var_name}")
        else:
            lines.append(f"  • Переменная окружения: ***")
        lines.append(f"  • Задержка после обеда: {state.config.get('after_lunch_delay', 5)} сек")
    else:
        lines.append(f"  • Ввод последовательности: ✗ (отключено)")

    lines.append("")

    if for_log:
        lines.append("ПРИ ЗАВЕРШЕНИИ ПРОГРАММЫ (Ctrl+C):")
    else:
        lines.append("🔌 ПРИ ЗАВЕРШЕНИИ ПРОГРАММЫ (Ctrl+C):")

    lines.append(f"  • Действие: Просто завершение программы")
    lines.append("=" * 70)

    # Текущий статус
    if simulation.is_work_hours(state):
        on_break, break_type = simulation.is_break_time(state)
        if on_break:
            lines.append(f"Текущий статус: Перерыв ({break_type})")
        else:
            lines.append(f"Текущий статус: Рабочее время - активность включена")
    else:
        if simulation.should_simulate_afterhours(state):
            if for_log:
                time_indicator = "Перед работой" if simulation.is_before_work(state) else "После работы"
                lines.append(f"Текущий статус: {time_indicator} - режим всплесков активности")
            else:
                time_indicator = "🌅 Перед работой" if simulation.is_before_work(state) else "🌙 После работы"
                lines.append(f"{time_indicator} - режим всплесков активности")
        else:
            if for_log:
                lines.append(f"Текущий статус: Внерабочее время - активность отключена")
            else:
                lines.append(f"🌙 Внерабочее время - активность отключена")

    lines.append("")
    lines.append("Для остановки нажмите Ctrl+C")
    lines.append("")

    if for_log:
        lines.append(f"Файл лога: {state.log_file_path}")
        lines.append(f"Начальная позиция мыши: {state.initial_mouse_position}")
        lines.append("=" * 70)

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
