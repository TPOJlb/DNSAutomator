import PyInstaller.__main__
import os
import shutil
import sys

def clean_build_folders():
    """Очищает папки сборки"""
    folders_to_clean = ['build', 'dist', '__pycache__']
    for folder in folders_to_clean:
        if os.path.exists(folder):
            print(f"🧹 Очищаем {folder}/")
            shutil.rmtree(folder)

def build_windows_exe():
    """Собирает Windows EXE файл"""
    print("🪟 Начинаем сборку Windows EXE...")
    
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
    if os.path.exists('icons.ico'):
        args.append('--icon=icons.ico')
        print("✅ Добавлена иконка")
    elif os.path.exists('icon.png'):
        print("⚠️  icons.ico не найден, используем icon.png")
        args.append('--icon=icon.png')
    
    # Добавляем конфиг если существует
    if os.path.exists('config.json'):
        args.append('--add-data=config.json;.')
        print("✅ Добавлен config.json")
    
    print("🏗️  Запускаем PyInstaller для Windows...")
    try:
        PyInstaller.__main__.run(args)
        print("✅ Windows EXE файл создан!")
        
        # Переименовываем для ясности
        exe_path = 'dist/DNSAutomator.exe'
        if os.path.exists(exe_path):
            print(f"📁 EXE файл: {exe_path}")
        return True
    except Exception as e:
        print(f"❌ Ошибка сборки: {e}")
        return False

def create_zip_archive():
    """Создает ZIP архив для Windows"""
    print("📦 Создаем ZIP архив...")
    
    exe_path = 'dist/DNSAutomator.exe'
    if not os.path.exists(exe_path):
        print("❌ EXE файл не найден")
        return False
    
    try:
        import zipfile
        zip_path = 'DNSAutomator_Windows.zip'
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(exe_path, 'DNSAutomator.exe')
            if os.path.exists('config.json'):
                zipf.write('config.json', 'config.json')
            if os.path.exists('README.txt'):
                zipf.write('README.txt', 'README.txt')
        
        print(f"✅ ZIP архив создан: {zip_path}")
        return True
    except Exception as e:
        print(f"❌ Ошибка создания ZIP: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Windows Builder")
    print("=" * 50)
    
    if build_windows_exe():
        create_zip_archive()
    else:
        print("❌ Сборка не удалась")
        sys.exit(1)