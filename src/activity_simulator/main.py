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

    # Загружаем конфигурацию
    simulation.CONFIG, simulation.SCHEDULE = config.load_or_create_config()
    # Ротация лог-файлов
    simulation.setup_log_rotation()
    # Инициализируем буферизованный логгер
    simulation.init_logger(simulation.log_file_path, simulation.CONFIG.get('verbose_logging', True))

    # Запуск слушателей
    _keyboard_listener = keyboard.Listener(on_press=listeners.on_keyboard_event)
    _mouse_listener = mouse.Listener(on_move=listeners.on_mouse_event,
                                     on_click=listeners.on_mouse_click)

    _keyboard_listener.start()
    _mouse_listener.start()

    simulation.initial_mouse_position = simulation.mouse_controller.position

    # Запуск потоков
    simulate_thread = Thread(target=simulation.simulate_activity, daemon=True)
    stats_thread = Thread(target=simulation.show_stats, daemon=True)

    simulate_thread.start()
    stats_thread.start()

    # === ВЫВОД ИНФОРМАЦИИ ===
    print("=" * 70)
    print("🚀 ПРОГРАММА СИМУЛЯЦИИ АКТИВНОСТИ ЗАПУЩЕНА")
    print("=" * 70)
    print(f"📅 Конфигурация: {config.get_config_filename()}")
    print(f"🖱️  Отслеживание: Мышь + Тачпад + Клавиатура")
    print()

    # Индикатор пятницы
    day_indicator = ""
    if simulation.SCHEDULE.get('is_friday', False):
        day_indicator = " 🎉 ПЯТНИЦА!"

    print(f"⏰ РАСПИСАНИЕ НА СЕГОДНЯ:{day_indicator}")
    print(f"  • Рабочее время: {simulation.SCHEDULE['work_start']} - {simulation.SCHEDULE['work_end']}")
    print(f"  • Обед: {simulation.SCHEDULE['lunch_start']} - {simulation.SCHEDULE['lunch_end']} " +
          f"({utils.time_str_to_minutes(simulation.SCHEDULE['lunch_end']) - utils.time_str_to_minutes(simulation.SCHEDULE['lunch_start'])} мин)")

    if simulation.SCHEDULE['breaks']:
        print(f"  • Перерывы:")
        for i, brk in enumerate(simulation.SCHEDULE['breaks'], 1):
            print(f"    {i}. {brk['start']} - {brk['end']} ({brk['duration']} мин)")
    else:
        print(f"  • Перерывы: нет")

    print()
    print(f"⚙️  ОСНОВНЫЕ ПАРАМЕТРЫ:")
    print(f"  • Порог бездействия: {simulation.CONFIG['min_idle_time']}-{simulation.CONFIG['max_idle_time']} сек")
    print(f"  • Интервал между действиями: {simulation.CONFIG['min_action_interval']}-{simulation.CONFIG['max_action_interval']} сек")
    print(f"  • Серия нажатий стрелок: {simulation.CONFIG['min_key_presses']}-{simulation.CONFIG['max_key_presses']} раз")
    print(f"  • Макс. диапазон мыши: {simulation.CONFIG['max_mouse_range']} пикс")

    print()
    print(f"🎯 ТИПЫ ДЕЙСТВИЙ:")
    print(f"  • Движение мыши: {'✓' if simulation.CONFIG['use_mouse_move'] else '✗'} (вес: {simulation.CONFIG['action_weight_mouse_move']})")
    print(f"  • Стрелки клавиатуры: {'✓' if simulation.CONFIG['use_keyboard'] else '✗'} (вес: {simulation.CONFIG['action_weight_keyboard']})")
    print(f"  • Ctrl+Tab: {'✓' if simulation.CONFIG['use_keyboard'] else '✗'} (вес: {simulation.CONFIG['action_weight_ctrl_tab']})")
    print(f"  • Клики мыши: {'✓' if simulation.CONFIG['use_mouse_click'] else '✗'} (вес: {simulation.CONFIG['action_weight_mouse_click']})")
    print(f"  • Shift (безопасный): {'✓' if simulation.CONFIG['natural_behavior'] else '✗'} (вес: {simulation.CONFIG['action_weight_safe_key']})")
    print(f"  • Естественное поведение: {'✓' if simulation.CONFIG['natural_behavior'] else '✗'}")

    print()
    afterhours_mode_names = {
        'disabled': '🚫 Отключен',
        'before_only': '🌅 Только до работы',
        'before_and_after': '🌅🌙 До и после работы'
    }
    print(f"🌙 ВНЕРАБОЧИЙ РЕЖИМ: {afterhours_mode_names.get(simulation.CONFIG['afterhours_mode'], simulation.CONFIG['afterhours_mode'])}")
    if simulation.CONFIG['afterhours_mode'] != 'disabled':
        print(f"  • Всплески активности: {simulation.CONFIG['afterhours_burst_duration_min']}-{simulation.CONFIG['afterhours_burst_duration_max']} сек")
        print(f"  • Интервал между всплесками: {simulation.CONFIG['afterhours_burst_interval_min']}-{simulation.CONFIG['afterhours_burst_interval_max']} мин")

    print()
    print(f"🍽️ ДЕЙСТВИЯ ПОСЛЕ ОБЕДА:")
    if simulation.CONFIG.get('after_lunch_action', False):
        sequence_display = simulation.CONFIG.get('after_lunch_sequence', '')
        # Маскируем текст, но показываем специальные клавиши
        masked_sequence = ""
        i = 0
        while i < len(sequence_display):
            if sequence_display[i] == '{':
                end = sequence_display.find('}', i)
                if end != -1:
                    masked_sequence += sequence_display[i:end+1]
                    i = end + 1
                else:
                    masked_sequence += '*'
                    i += 1
            else:
                masked_sequence += '*'
                i += 1

        print(f"  • Ввод последовательности: ✓ ({masked_sequence})")
        print(f"  • Задержка после обеда: {simulation.CONFIG.get('after_lunch_delay', 5)} сек")
    else:
        print(f"  • Ввод последовательности: ✗ (отключено)")

    print()
    print(f"🔌 ПРИ ЗАВЕРШЕНИИ ПРОГРАММЫ (Ctrl+C):")
    print(f"  • Действие: Просто завершение программы")

    print("=" * 70)

    # Проверяем текущий статус
    if simulation.is_work_hours():
        on_break, break_type = simulation.is_break_time()
        if on_break:
            print(f"☕ Текущий статус: Перерыв ({break_type})")
        else:
            print(f"💼 Текущий статус: Рабочее время - активность включена")
    else:
        if simulation.should_simulate_afterhours():
            time_indicator = "🌅 Перед работой" if simulation.is_before_work() else "🌙 После работы"
            print(f"{time_indicator} - режим всплесков активности")
        else:
            print(f"🌙 Внерабочее время - активность отключена")

    print()
    print("Для остановки нажмите Ctrl+C")
    print()

    # === СОХРАНЕНИЕ ИНФОРМАЦИОННОЙ ЧАСТИ В ЛОГ ===
    if simulation.CONFIG['verbose_logging']:
        simulation.log("=" * 70)
        simulation.log("ПРОГРАММА СИМУЛЯЦИИ АКТИВНОСТИ ЗАПУЩЕНА")
        simulation.log("=" * 70)
        simulation.log(f"Конфигурация: {config.get_config_filename()}")
        simulation.log(f"Отслеживание: Мышь + Тачпад + Клавиатура")
        simulation.log("")

        day_log_indicator = ""
        if simulation.SCHEDULE.get('is_friday', False):
            day_log_indicator = " (ПЯТНИЦА - короткий день)"

        simulation.log(f"РАСПИСАНИЕ НА СЕГОДНЯ:{day_log_indicator}")
        simulation.log(f"  • Рабочее время: {simulation.SCHEDULE['work_start']} - {simulation.SCHEDULE['work_end']}")
        simulation.log(f"  • Обед: {simulation.SCHEDULE['lunch_start']} - {simulation.SCHEDULE['lunch_end']} " +
                      f"({utils.time_str_to_minutes(simulation.SCHEDULE['lunch_end']) - utils.time_str_to_minutes(simulation.SCHEDULE['lunch_start'])} мин)")

        if simulation.SCHEDULE['breaks']:
            simulation.log(f"  • Перерывы:")
            for i, brk in enumerate(simulation.SCHEDULE['breaks'], 1):
                simulation.log(f"    {i}. {brk['start']} - {brk['end']} ({brk['duration']} мин)")
        else:
            simulation.log(f"  • Перерывы: нет")

        simulation.log("")
        simulation.log("ОСНОВНЫЕ ПАРАМЕТРЫ:")
        simulation.log(f"  • Порог бездействия: {simulation.CONFIG['min_idle_time']}-{simulation.CONFIG['max_idle_time']} сек")
        simulation.log(f"  • Интервал между действиями: {simulation.CONFIG['min_action_interval']}-{simulation.CONFIG['max_action_interval']} сек")
        simulation.log(f"  • Серия нажатий стрелок: {simulation.CONFIG['min_key_presses']}-{simulation.CONFIG['max_key_presses']} раз")
        simulation.log(f"  • Макс. диапазон мыши: {simulation.CONFIG['max_mouse_range']} пикс")

        simulation.log("")
        simulation.log("ТИПЫ ДЕЙСТВИЙ:")
        simulation.log(f"  • Движение мыши: {'✓' if simulation.CONFIG['use_mouse_move'] else '✗'} (вес: {simulation.CONFIG['action_weight_mouse_move']})")
        simulation.log(f"  • Стрелки клавиатуры: {'✓' if simulation.CONFIG['use_keyboard'] else '✗'} (вес: {simulation.CONFIG['action_weight_keyboard']})")
        simulation.log(f"  • Ctrl+Tab: {'✓' if simulation.CONFIG['use_keyboard'] else '✗'} (вес: {simulation.CONFIG['action_weight_ctrl_tab']})")
        simulation.log(f"  • Клики мыши: {'✓' if simulation.CONFIG['use_mouse_click'] else '✗'} (вес: {simulation.CONFIG['action_weight_mouse_click']})")
        simulation.log(f"  • Shift (безопасный): {'✓' if simulation.CONFIG['natural_behavior'] else '✗'} (вес: {simulation.CONFIG['action_weight_safe_key']})")
        simulation.log(f"  • Естественное поведение: {'✓' if simulation.CONFIG['natural_behavior'] else '✗'}")

        simulation.log("")
        afterhours_mode_names = {
            'disabled': '🚫 Отключен',
            'before_only': '🌅 Только до работы',
            'before_and_after': '🌅🌙 До и после работы'
        }
        simulation.log(f"ВНЕРАБОЧИЙ РЕЖИМ: {afterhours_mode_names.get(simulation.CONFIG['afterhours_mode'], simulation.CONFIG['afterhours_mode'])}")
        if simulation.CONFIG['afterhours_mode'] != 'disabled':
            simulation.log(f"  • Всплески активности: {simulation.CONFIG['afterhours_burst_duration_min']}-{simulation.CONFIG['afterhours_burst_duration_max']} сек")
            simulation.log(f"  • Интервал между всплесками: {simulation.CONFIG['afterhours_burst_interval_min']}-{simulation.CONFIG['afterhours_burst_interval_max']} мин")

        simulation.log("")
        simulation.log("ДЕЙСТВИЯ ПОСЛЕ ОБЕДА:")
        if simulation.CONFIG.get('after_lunch_action', False):
            sequence_display = simulation.CONFIG.get('after_lunch_sequence', '')
            masked_sequence = ""
            i = 0
            while i < len(sequence_display):
                if sequence_display[i] == '{':
                    end = sequence_display.find('}', i)
                    if end != -1:
                        masked_sequence += sequence_display[i:end+1]
                        i = end + 1
                    else:
                        masked_sequence += '*'
                        i += 1
                else:
                    masked_sequence += '*'
                    i += 1

            simulation.log(f"  • Ввод последовательности: ✓ ({masked_sequence})")
            simulation.log(f"  • Задержка после обеда: {simulation.CONFIG.get('after_lunch_delay', 5)} сек")
        else:
            simulation.log(f"  • Ввод последовательности: ✗ (отключено)")

        simulation.log("")
        simulation.log("ПРИ ЗАВЕРШЕНИИ ПРОГРАММЫ (Ctrl+C):")
        simulation.log(f"  • Действие: Просто завершение программы")

        simulation.log("=" * 70)

        # Текущий статус
        if simulation.is_work_hours():
            on_break, break_type = simulation.is_break_time()
            if on_break:
                simulation.log(f"Текущий статус: Перерыв ({break_type})")
            else:
                simulation.log(f"Текущий статус: Рабочее время - активность включена")
        else:
            if simulation.should_simulate_afterhours():
                time_indicator = "Перед работой" if simulation.is_before_work() else "После работы"
                simulation.log(f"Текущий статус: {time_indicator} - режим всплесков активности")
            else:
                simulation.log(f"Текущий статус: Внерабочее время - активность отключена")

        simulation.log("")
        simulation.log(f"Файл лога: {simulation.log_file_path}")
        simulation.log(f"Начальная позиция мыши: {simulation.initial_mouse_position}")
        simulation.log("=" * 70)

    # === ОБРАБОТКА ЗАВЕРШЕНИЯ ===
    # Флаг для корректного завершения
    running = True

    def signal_handler(sig: int, frame) -> None:
        """Обработчик сигнала Ctrl+C"""
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, signal_handler)

    # Главный цикл - ждем завершения
    try:
        while running:
            time.sleep(0.5)
            # Проверяем, завершилась ли симуляция (через ExitSimulation)
            if simulation.simulation_finished:
                running = False
    except KeyboardInterrupt:
        pass

    # Обработка завершения - определяем причину
    if simulation.simulation_finished:
        # Симуляция завершилась сама (через ExitSimulation)
        print("\n\n🏁 Программа завершена автоматически")
    else:
        # Обычное завершение (Ctrl+C или пользователь)
        print("\n\n🛑 Программа остановлена пользователем")

    if simulation.CONFIG['verbose_logging']:
        print(f"📄 Лог сохранён в файл: {simulation.log_file_path}")
        simulation.log("")
        simulation.log("=" * 70)
        simulation.log(f"Программа завершена. Всего действий: {len(simulation.action_history)}")
        simulation.log("=" * 70)

    # При нажатии Ctrl-C программа просто завершается
    print("👋 Программа завершена. До свидания!")
    sys.exit(0)


if __name__ == "__main__":
    main()