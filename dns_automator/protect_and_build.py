import os
import shutil
import subprocess
import sys

def protect_code():
    """Защищает код с помощью PyArmor"""
    print("🔒 Защищаем код...")
    
    # Очищаем предыдущие сборки
    for folder in ['protected_build', 'build', 'dist', '__pycache__']:
        if os.path.exists(folder):
            print(f"🧹 Очищаем {folder}/")
            shutil.rmtree(folder)
    
    try:
        import pyarmor
        print("🛡️  Используем PyArmor для защиты...")
        pyarmor.obfuscate(
            'app.py',
            output='protected_build',
            restrict_mode=4,
            advanced_mode=2,
            enable_suffix=1
        )
        print("✅ Код защищен")
        return True
    except ImportError:
        print("❌ PyArmor не установлен")
        print("Установите: pip3 install pyarmor")
        return False
    except Exception as e:
        print(f"❌ Ошибка защиты: {e}")
        return False

def run_build_command(script_name, platform_name):
    """Запускает скрипт сборки и возвращает результат"""
    print(f"\n🏗️  Сборка {platform_name}...")
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {platform_name} собрано")
            return True
        else:
            print(f"❌ Ошибка сборки {platform_name}:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Ошибка при запуске {script_name}: {e}")
        return False

def build_protected_apps():
    """Собирает защищенные приложения для всех платформ"""
    print("🏗️  Собираем защищенные приложения...")
    
    # Копируем необходимые файлы
    for file in ['icons.icns', 'icons.ico', 'config.json']:
        if os.path.exists(file):
            shutil.copy2(file, 'protected_build/')
    
    # Сохраняем текущую директорию
    original_dir = os.getcwd()
    os.chdir('protected_build')
    
    success = True
    
    try:
        # Сборка для macOS
        if not run_build_command('../build_mac.py', 'macOS'):
            success = False
        
        # Сборка для Windows
        if not run_build_command('../build_windows.py', 'Windows'):
            success = False
        
        return success
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return False
    finally:
        os.chdir(original_dir)

if __name__ == "__main__":
    print("=" * 50)
    print("🔒 Protected Builder")
    print("=" * 50)
    
    if protect_code():
        if build_protected_apps():
            print("\n✅ ЗАЩИЩЕННАЯ СБОРКА ЗАВЕРШЕНА!")
        else:
            print("\n❌ ЗАЩИЩЕННАЯ СБОРКА НЕ УДАЛАСЬ!")
            sys.exit(1)
    else:
        sys.exit(1)