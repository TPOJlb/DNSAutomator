import PyInstaller.__main__
import os
import shutil
import subprocess
import sys

def clean_build_folders():
    """Очищает папки сборки"""
    folders_to_clean = ['build', 'dist', '__pycache__']
    for folder in folders_to_clean:
        if os.path.exists(folder):
            print(f"🧹 Очищаем {folder}/")
            shutil.rmtree(folder)

def build_mac_app():
    """Собирает macOS приложение"""
    print("🍎 Начинаем сборку macOS приложения...")
    
    clean_build_folders()
    
    # Проверяем необходимые файлы
    if not os.path.exists('app.py'):
        print("❌ ОШИБКА: app.py не найден!")
        return False
    
    # Подготавливаем аргументы для PyInstaller
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
    if os.path.exists('icons.icns'):
        args.append('--icon=icons.icns')
        print("✅ Добавлена иконка")
    
    # Добавляем конфиг если существует
    if os.path.exists('config.json'):
        args.append('--add-data=config.json:.')
        print("✅ Добавлен config.json")
    
    print("🏗️  Запускаем PyInstaller...")
    try:
        PyInstaller.__main__.run(args)
        print("✅ macOS приложение создано!")
        return True
    except Exception as e:
        print(f"❌ Ошибка сборки: {e}")
        return False

def create_dmg():
    """Создает DMG файл"""
    print("📦 Создаем DMG файл...")
    
    app_path = 'dist/DNSAutomator.app'
    if not os.path.exists(app_path):
        print("❌ Приложение не найдено")
        return False
    
    # Проверяем установлен ли create-dmg
    try:
        result = subprocess.run(['which', 'create-dmg'], 
                              capture_output=True, text=True, check=True)
        if not result.stdout.strip():
            print("ℹ️  create-dmg не установлен")
            print("Установите: brew install create-dmg")
            return False
    except subprocess.CalledProcessError:
        print("ℹ️  create-dmg не установлен")
        return False
    
    # Создаем DMG
    try:
        subprocess.run([
            'create-dmg',
            '--volname', 'DNSAutomator',
            '--window-pos', '200', '120',
            '--window-size', '800', '400',
            '--icon-size', '100',
            '--icon', 'DNSAutomator.app', '200', '190',
            '--hide-extension', 'DNSAutomator.app',
            '--app-drop-link', '600', '190',
            '--no-internet-enable',
            'DNSAutomator.dmg',
            app_path
        ], check=True)
        print("✅ DMG файл создан: DNSAutomator.dmg")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка создания DMG: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 macOS Builder")
    print("=" * 50)
    
    if build_mac_app():
        create_dmg()
    else:
        print("❌ Сборка не удалась")
        sys.exit(1)