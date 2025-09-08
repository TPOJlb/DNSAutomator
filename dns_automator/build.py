#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_dependencies():
    """Проверяет установлены ли зависимости"""
    print("🔍 Проверяем зависимости...")
    
    dependencies = {
        'pyinstaller': 'PyInstaller',
        'pyarmor': 'PyArmor', 
        'requests': 'Requests',
        'gspread': 'gspread',
        'oauth2client': 'oauth2client'
    }
    
    missing = []
    for package, name in dependencies.items():
        try:
            if package == 'pyinstaller':
                import PyInstaller
            elif package == 'pyarmor':
                import pyarmor
            elif package == 'requests':
                import requests
            elif package == 'gspread':
                import gspread
            elif package == 'oauth2client':
                import oauth2client
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name}")
            missing.append(package)
    
    return missing

def check_files_exist():
    """Проверяет существование файлов после сборки"""
    print("\n🔎 Проверяем созданные файлы...")
    
    files_to_check = [
        ('dist/DNSAutomator.app', 'macOS приложение'),
        ('dist/DNSAutomator.exe', 'Windows EXE'),
        ('DNSAutomator.dmg', 'macOS DMG'),
        ('DNSAutomator_Windows.zip', 'Windows ZIP')
    ]
    
    found_files = []
    for file_path, description in files_to_check:
        if os.path.exists(file_path):
            print(f"✅ {description}: {file_path}")
            found_files.append((file_path, description))
        else:
            print(f"❌ {description}: не найден")
    
    return found_files

def run_command(command, description):
    """Запускает команду и возвращает результат"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Ошибка: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False

def main():
    print("=" * 50)
    print("🚀 DNSAutomator Builder")
    print("Python:", sys.version)
    print("=" * 50)
    
    # Проверяем файлы
    if not os.path.exists('app.py'):
        print("❌ ОШИБКА: app.py не найден!")
        sys.exit(1)
    
    if not os.path.exists('icon.png'):
        print("❌ ОШИБКА: icon.png не найден!")
        sys.exit(1)
    
    # Проверяем зависимости
    missing = check_dependencies()
    if missing:
        print(f"\n❌ Отсутствуют: {', '.join(missing)}")
        print("Установите: pip3 install " + " ".join(missing))
        sys.exit(1)
    
    # Конвертируем иконки
    print("\n🔄 Конвертируем иконки...")
    if not run_command([sys.executable, 'convert_icons.py'], "Конвертация иконок"):
        print("❌ Ошибка конвертации иконок")
        sys.exit(1)
    
    # Выбор режима сборки
    print("\n🎯 Выберите режим сборки:")
    print("1. Обычная сборка (macOS + Windows)")
    print("2. Защищенная сборка (macOS + Windows)")
    print("3. Только macOS")
    print("4. Только Windows")
    
    choice = input("Ваш выбор (1-4): ").strip()
    
    success = False
    
    if choice == "1":
        print("\n🏗️  Обычная сборка для всех платформ...")
        success1 = run_command([sys.executable, 'build_mac.py'], "Сборка macOS")
        success2 = run_command([sys.executable, 'build_windows.py'], "Сборка Windows")
        success = success1 or success2
        
    elif choice == "2":
        print("\n🔒 Защищенная сборка для всех платформ...")
        success = run_command([sys.executable, 'protect_and_build.py'], "Защищенная сборка")
        
    elif choice == "3":
        print("\n🍎 Сборка только для macOS...")
        success = run_command([sys.executable, 'build_mac.py'], "Сборка macOS")
        
    elif choice == "4":
        print("\n🪟 Сборка только для Windows...")
        success = run_command([sys.executable, 'build_windows.py'], "Сборка Windows")
        
    else:
        print("❌ Неверный выбор!")
        sys.exit(1)
    
    # Проверяем результат
    if success:
        print("\n" + "=" * 50)
        print("✅ ПРОЦЕСС СБОРКИ ЗАВЕРШЕН!")
        
        # Проверяем какие файлы реально создались
        found_files = check_files_exist()
        
        if found_files:
            print("\n📁 СОЗДАННЫЕ ФАЙЛЫ:")
            for file_path, description in found_files:
                print(f"   {description}: {file_path}")
        else:
            print("\n❌ ФАЙЛЫ НЕ СОЗДАНЫ!")
            print("Проверьте логи выше для диагностики ошибок")
            
        print("=" * 50)
    else:
        print(f"\n❌ ОШИБКА СБОРКИ")
        print("Подробности смотрите в логах выше")
        sys.exit(1)

if __name__ == "__main__":
    main()