#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil

def print_step(step):
    print(f"\n{'='*60}")
    print(f"🚀 {step}")
    print(f"{'='*60}")

def run_command(cmd, description):
    print(f"\n▶️  {description}...")
    print(f"   Команда: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ Успешно")
            if result.stdout:
                print(f"   Вывод: {result.stdout[:200]}...")
            return True
        else:
            print(f"   ❌ Ошибка (код: {result.returncode})")
            if result.stderr:
                print(f"   STDERR: {result.stderr}")
            if result.stdout:
                print(f"   STDOUT: {result.stdout}")
            return False
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
        return False

def check_files():
    print("\n📁 ПРОВЕРКА ФАЙЛОВ:")
    files = [
        ('app.py', 'Основной код'),
        ('icon.png', 'Иконка PNG'),
        ('icons.icns', 'Иконка macOS'),
        ('icons.ico', 'Иконка Windows'),
        ('config.json', 'Конфигурация')
    ]
    
    for file, desc in files:
        exists = os.path.exists(file)
        status = "✅" if exists else "❌"
        print(f"   {status} {desc}: {file}")

def clean_build():
    print("\n🧹 ОЧИСТКА ПАПОК СБОРКИ:")
    for folder in ['build', 'dist', '__pycache__']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"   Удалено: {folder}/")
        else:
            print(f"   Не существует: {folder}/")

def main():
    print("🎯 ПРОСТАЯ СБОРКА БЕЗ ЗАЩИТЫ")
    print(f"Рабочая директория: {os.getcwd()}")
    print(f"Python: {sys.version}")
    
    # Проверяем файлы
    check_files()
    
    if not os.path.exists('app.py'):
        print("❌ ОШИБКА: app.py не найден!")
        return False
    
    # Очищаем предыдущие сборки
    clean_build()
    
    # Шаг 1: Конвертация иконок
    print_step("ШАГ 1: КОНВЕРТАЦИЯ ИКОНОК")
    if not run_command([sys.executable, 'convert_icons.py'], "Конвертация иконок"):
        print("⚠️  Продолжаем без иконок")
    
    # Шаг 2: Сборка macOS
    print_step("ШАГ 2: СБОРКА macOS")
    if not run_command([sys.executable, 'build_mac.py'], "Сборка macOS приложения"):
        print("❌ Ошибка сборки macOS")
        return False
    
    # Шаг 3: Сборка Windows
    print_step("ШАГ 3: СБОРКА WINDOWS")
    if not run_command([sys.executable, 'build_windows.py'], "Сборка Windows EXE"):
        print("❌ Ошибка сборки Windows")
        return False
    
    # Проверяем результаты
    print_step("РЕЗУЛЬТАТЫ СБОРКИ")
    
    created_files = []
    for path, desc in [
        ('dist/DNSAutomator.app', 'macOS приложение'),
        ('dist/DNSAutomator.exe', 'Windows EXE'),
        ('DNSAutomator.dmg', 'macOS DMG'),
        ('DNSAutomator_Windows.zip', 'Windows ZIP')
    ]:
        if os.path.exists(path):
            created_files.append((path, desc))
            size = os.path.getsize(path) if os.path.isfile(path) else "папка"
            print(f"✅ {desc}: {path} ({size})")
        else:
            print(f"❌ {desc}: не создан")
    
    if created_files:
        print(f"\n🎉 УСПЕХ! Создано {len(created_files)} файлов")
        return True
    else:
        print("\n😞 НИЧЕГО НЕ СОЗДАНО")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n" + "="*60)
        print("✅ СБОРКА ЗАВЕРШЕНА УСПЕШНО!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ СБОРКА ЗАВЕРШИЛАСЬ С ОШИБКАМИ!")
        print("="*60)
        sys.exit(1)