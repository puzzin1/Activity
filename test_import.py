#!/usr/bin/env python3
"""
Тестовый скрипт для проверки импорта и основных функций пакета activity_simulator.
Не запускает симуляцию активности.
"""

import sys
import os

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("=" * 70)
    print("🧪 ТЕСТ ИМПОРТА ПАКЕТА activity_simulator")
    print("=" * 70)

    # 1. Импорт основных модулей из корневого пакета
    print("1. Импорт основных модулей из корневого пакета...")
    from activity_simulator import (
        load_or_create_config,
        get_config_filename,
        DEFAULT_CONFIG,
    )
    from activity_simulator.simulation import (
        simulate_activity,
        show_stats,
    )
    from activity_simulator.listeners import (
        on_keyboard_event,
        on_mouse_event,
        on_mouse_click,
    )
    from activity_simulator.utils import (
        lock_computer,
        shutdown_computer,
        parse_key_sequence,
    )
    from activity_simulator.main import main
    print("   ✅ Все модули успешно импортированы")

    # 2. Проверка конфигурации
    print("\n2. Проверка загрузки конфигурации...")
    config, schedule = load_or_create_config()
    print(f"   ✅ Конфигурация загружена:")
    print(f"      • Файл: {get_config_filename()}")
    print(f"      • Рабочее время: {schedule['work_start']} - {schedule['work_end']}")
    print(f"      • Обед: {schedule['lunch_start']} - {schedule['lunch_end']}")
    print(f"      • Перерывов: {len(schedule.get('breaks', []))}")

    # 3. Проверка DEFAULT_CONFIG
    print("\n3. Проверка DEFAULT_CONFIG...")
    print(f"   ✅ Параметров в DEFAULT_CONFIG: {len(DEFAULT_CONFIG)}")
    print(f"      • min_idle_time: {DEFAULT_CONFIG['min_idle_time']}")
    print(f"      • max_idle_time: {DEFAULT_CONFIG['max_idle_time']}")
    print(f"      • afterhours_mode: {DEFAULT_CONFIG['afterhours_mode']}")

    # 4. Проверка утилит
    print("\n4. Проверка утилит...")

    # Парсинг последовательности клавиш
    test_sequence = "username{Tab}password{Enter}"
    parsed = parse_key_sequence(test_sequence)
    print(f"   ✅ Парсинг последовательности: {test_sequence}")
    print(f"      -> {parsed}")

    # Проверка доступности функций блокировки/выключения (без выполнения)
    print(f"   ✅ Функция lock_computer доступна: {lock_computer.__name__}")
    print(f"   ✅ Функция shutdown_computer доступна: {shutdown_computer.__name__}")

    # 5. Проверка доступности main
    print("\n5. Проверка функции main...")
    print(f"   ✅ main доступна: {main.__name__}")
    print(f"      Документация: {main.__doc__[:100]}...")

    # 6. Проверка доступа к функциям симуляции
    print("\n6. Проверка функций симуляции...")
    print(f"   ✅ simulate_activity доступна: {simulate_activity.__name__}")
    print(f"   ✅ show_stats доступна: {show_stats.__name__}")

    print("\n" + "=" * 70)
    print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 70)

except Exception as e:
    print(f"\n❌ ОШИБКА ПРИ ТЕСТИРОВАНИИ: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)