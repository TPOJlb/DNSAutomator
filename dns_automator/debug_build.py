#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import time

def print_header(text):
    print("\n" + "=" * 60)
    print(f"🔍 {text}")
    print("=" * 60)

def run_command(command, description, show_output=True):
    """Запускает команду и показывает реальный вывод"""
    print(f"\n▶️  {description}...")
    print(f"   Команда: {' '.join(command)}")
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        
        if show_output or result.returncode != 0:
            if result.stdout:
                print("   STDOUT:")
                print(result.stdout[:1000] + "..." if len(result.stdout) > 1000 else result.stdout)
            if result.stderr:
                print("   STDERR:")
                print(result.stderr[:1000] + "..." if len(result.stderr) > 1000 else result.stderr)
        
        if result.returncode == 0:
            print(f"   ✅ Успешно")
            return True
        else:
            print(f"   ❌ Ошибка (код: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ⏰ Таймаут команды")
        return False
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
        return False

def check_files():
    """Проверяет какие файлы существуют"""
    print_header("ПРОВЕРКА ФАЙЛОВ")
    
    files_to_check = [
        ('app.py', 'Основной код'),
        ('icon.png', 'Иконка PNG'),
        ('config.json', 'Конфигурация'),
        ('icons.icns', 'Иконка macOS'),
        ('icons.ico', 'Иконка Windows'),
    ]
    
    for file, desc in files_to_check:
        exists = os.path.exists(file)
        status = '✅' if exists else '❌'
        print(f"{status} {desc}: {file} {'(существует)' if exists else '(не найден)'}")

def check_directories():
    """Проверяет существование папок"""
    print_header("ПРОВЕРКА ПАПОК")
    
    dirs_to_check = ['.', 'dist', 'build', 'protected_build']
    
    for dir_path in dirs_to_check:
        exists = os.path.exists(dir_path)
        status = '✅' if exists else '❌'
        size_info = ""

        if exists and dir_path != '.':
            try:
                if os.path.isdir(dir_path):
                    item_count = len(os.listdir(dir_path))
                    size_info = f" ({item_count} items)"
                else:
                    size_info = f" ({os.path.getsize(dir_path)} bytes)"
            except:
                size_info = " (ошибка доступа)"
        
        print(f"{status} {dir_path}/{size_info}")

def clean_build():
    """Очищает папки сборки"""
    print_header("ОЧИСТКА ПАПОК СБОРКИ")
    
    for folder in ['build', 'dist', 'protected_build', '__pycache__']:
        if os.path.exists(folder):
            print(f"🧹 Удаляем {folder}/")
            shutil.rmtree(folder)
        else:
            print(f"📁 {folder}/ не существует")

def protect_code():
    """Защищает код с помощью PyArmor"""
    print_header("ШАГ 2: ЗАЩИТА КОДА")
    
    # Создаем временный Python файл для защиты
    protect_script = """
import pyarmor
try:
    # Новый API PyArmor
    pyarmor.cli.gen(
        '--output', 'protected_build',
        '--restrict', '4',
        '--advanced', '2',
        '--enable-suffix',
        '--package-runtime', '0',
        'app.py'
    )
    print("✅ Код защищен успешно")
except Exception as e:
    print(f"❌ Ошибка защиты: {e}")
    exit(1)
"""
    
    with open('temp_protect.py', 'w') as f:
        f.write(protect_script)
    
    success = run_command([sys.executable, 'temp_protect.py'], "Защита кода PyArmor", True)
    
    # Удаляем временный файл
    if os.path.exists('temp_protect.py'):
        os.remove('temp_protect.py')
    
    return success

def main():
    print("🚀 ЗАПУСК РЕАЛЬНОЙ ПРОВЕРКИ СБОРКИ")
    print(f"Рабочая директория: {os.getcwd()}")
    print(f"Python: {sys.version}")
    
    # Проверяем текущее состояние
    check_files()
    check_directories()
    
    # Очищаем предыдущие сборки
    clean_build()
    
    # Шаг 1: Конвертация иконок
    print_header("ШАГ 1: КОНВЕРТАЦИЯ ИКОНОК")
    success_icons = run_command([sys.executable, 'convert_icons.py'], "Конвертация иконок", True)
    
    if not success_icons:
        print("❌ Ошибка конвертации иконок!")
        return False
    
    # Шаг 2: Защита кода
    success_protect = protect_code()
    if not success_protect:
        print("❌ Ошибка защиты кода!")
        return False
    
    # Копируем файлы в protected_build
    print_header("ШАГ 3: КОПИРОВАНИЕ ФАЙЛОВ")
    for file in ['icons.icns', 'icons.ico', 'config.json']:
        if os.path.exists(file):
            shutil.copy2(file, 'protected_build/')
            print(f"✅ Скопирован {file}")
        else:
            print(f"⚠️  Файл {file} не существует")
    
    # Шаг 4: Сборка macOS
    print_header("ШАГ 4: СБОРКА macOS")
    original_dir = os.getcwd()
    os.chdir('protected_build')
    success_mac = run_command([sys.executable, '../build_mac.py'], "Сборка macOS приложения", True)
    os.chdir(original_dir)
    
    # Проверяем результаты
    print_header("ФИНАЛЬНАЯ ПРОВЕРКА")
    check_directories()
    
    # Проверяем конкретные файлы
    mac_app = 'protected_build/dist/DNSAutomator.app'
    windows_exe = 'protected_build/dist/DNSAutomator.exe'
    dmg_file = 'protected_build/DNSAutomator.dmg'
    zip_file = 'protected_build/DNSAutomator_Windows.zip'
    
    files_created = []
    
    for path, desc in [
        (mac_app, 'macOS приложение'),
        (windows_exe, 'Windows EXE'),
        (dmg_file, 'macOS DMG'),
        (zip_file, 'Windows ZIP')
    ]:
        if os.path.exists(path):
            files_created.append((path, desc))
            print(f"✅ {desc}: {path}")
        else:
            print(f"❌ {desc}: не создан")
    
    if files_created:
        print_header("🎉 УСПЕХ! СОЗДАННЫЕ ФАЙЛЫ:")
        for path, desc in files_created:
            print(f"📦 {desc}:")
            print(f"   {os.path.abspath(path)}")
            
            # Показываем размер
            if os.path.isfile(path):
                size = os.path.getsize(path)
                print(f"   Размер: {size:,} bytes ({size/1024/1024:.1f} MB)")
            elif os.path.isdir(path):
                print(f"   Папка приложения")
    else:
        print_header("😞 НИЧЕГО НЕ СОЗДАНО")
        print("Проверьте логи выше для диагностики ошибок")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n" + "=" * 60)
            print("🎉 РЕАЛЬНАя СБОРКА ЗАВЕРШЕНА УСПЕШНО!")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ СБОРКА ЗАВЕРШИЛАСЬ С ОШИБКАМИ!")
            print("=" * 60)
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)