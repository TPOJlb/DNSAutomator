#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import time

def print_step(message):
    print(f"\n{'='*60}")
    print(f"🚀 {message}")
    print(f"{'='*60}")

def run_command(cmd, description, timeout=600):
    print(f"\n▶️  {description}...")
    print(f"   Команда: {' '.join(cmd)}")
    
    try:
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        end_time = time.time()
        
        if result.returncode == 0:
            print(f"   ✅ Успешно ({end_time - start_time:.1f} сек)")
            if result.stdout:
                print(f"   Вывод: {result.stdout[:500]}...")
            return True
        else:
            print(f"   ❌ Ошибка (код: {result.returncode}, время: {end_time - start_time:.1f} сек)")
            if result.stderr:
                print(f"   Ошибка: {result.stderr}")
            if result.stdout:
                print(f"   Вывод: {result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ⏰ Таймаут ({timeout} сек)")
        return False
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
        return False

def clean_build():
    """Очищает папки сборки"""
    print("\n🧹 Очищаем папки сборки...")
    for folder in ['build', 'dist', '__pycache__']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"   Удалено: {folder}/")

def main():
    print("🎯 СБОРКА WINDOWS EXE")
    print(f"Рабочая директория: {os.getcwd()}")
    
    # Проверяем необходимые файлы
    if not os.path.exists('app.py'):
        print("❌ ОШИБКА: app.py не найден!")
        return False
    
    # Очищаем предыдущие сборки
    clean_build()
    
    # Шаг 1: Подготавливаем аргументы для PyInstaller
    print_step("ПОДГОТОВКА АРГУМЕНТОВ")
    
    args = [
        'app.py',
        '--onefile',
        '--windowed',
        '--name=DNSAutomator',
        '--hidden-import=tkinter',
        '--hidden-import=requests',
        '--hidden-import=gspread',
        '--hidden-import=oauth2client.service_account',
        '--hidden-import=xml.etree.ElementTree',
        '--hidden-import=json',
        '--hidden-import=os',
        '--hidden-import=time',
        '--hidden-import=re',
        '--hidden-import=socket',
        '--hidden-import=threading',
        '--hidden-import=atexit',
    ]
    
    # Добавляем иконку если существует
    if os.path.exists('icons.ico'):
        args.append('--icon=icons.ico')
        print("✅ Добавлена иконка Windows")
    elif os.path.exists('icon.png'):
        args.append('--icon=icon.png')
        print("✅ Добавлена PNG иконка")
    else:
        print("⚠️  Иконка не найдена")
    
    # Добавляем конфиг если существует (ИСПРАВЛЕНО: используем : вместо ;)
    if os.path.exists('config.json'):
        args.append('--add-data=config.json:.')
        print("✅ Добавлен config.json")
    
    print("Аргументы PyInstaller:")
    for arg in args:
        print(f"  {arg}")
    
    # Шаг 2: Запускаем сборку
    print_step("ЗАПУСК СБОРКИ WINDOWS EXE")
    print("⏳ Сборка может занять 5-15 минут...")
    
    success = run_command(['pyinstaller'] + args, "Сборка Windows EXE", timeout=900)
    
    # Шаг 3: Проверяем результат
    print_step("ПРОВЕРКА РЕЗУЛЬТАТОВ")
    
    exe_path = 'dist/DNSAutomator.exe'
    if os.path.exists(exe_path):
        file_size = os.path.getsize(exe_path)
        print(f"✅ WINDOWS EXE СОЗДАН!")
        print(f"📁 Файл: {exe_path}")
        print(f"📊 Размер: {file_size:,} байт ({file_size/1024/1024:.1f} MB)")
        
        # Создаем ZIP архив для удобства
        import zipfile
        zip_path = 'DNSAutomator_Windows.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(exe_path, 'DNSAutomator.exe')
            if os.path.exists('config.json'):
                zipf.write('config.json', 'config.json')
        
        print(f"📦 ZIP архив: {zip_path}")
        return True
    else:
        print("❌ EXE файл не создан")
        # Проверяем есть ли другие файлы в dist
        if os.path.exists('dist'):
            files = os.listdir('dist')
            print(f"📁 Содержимое папки dist: {files}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n" + "="*60)
            print("🎉 СБОРКА WINDOWS EXE ЗАВЕРШЕНА УСПЕШНО!")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("❌ СБОРКА НЕ УДАЛАСЬ!")
            print("="*60)
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Сборка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)