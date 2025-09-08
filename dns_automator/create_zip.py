#!/usr/bin/env python3
import os
import zipfile
import shutil

def create_windows_zip():
    print("📦 СОЗДАНИЕ WINDOWS ZIP АРХИВА")
    
    # Проверяем что EXE файл существует
    exe_path = 'dist/DNSAutomator.exe'
    if not os.path.exists(exe_path):
        print("❌ EXE файл не найден!")
        return False
    
    # Создаем временную папку для упаковки
    temp_dir = 'windows_package'
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    # Копируем EXE файл
    shutil.copy2(exe_path, os.path.join(temp_dir, 'DNSAutomator.exe'))
    print("✅ EXE файл скопирован")
    
    # Копируем конфиг если существует
    if os.path.exists('config.json'):
        shutil.copy2('config.json', os.path.join(temp_dir, 'config.json'))
        print("✅ Config файл скопирован")
    
    # Копируем README если существует, или создаем простой
    readme_path = os.path.join(temp_dir, 'README.txt')
    with open(readme_path, 'w') as f:
        f.write("""DNS Automator - Установка и использование

1. Запустите DNSAutomator.exe
2. Настройте параметры в интерфейсе
3. Нажмите "Run DNS Setup" для начала работы

Требования:
- Windows 7/8/10/11
- Доступ к интернету
- API ключи от Namecheap

Для проблем и вопросов:
- Проверьте config.json настройки
- Убедитесь что IP адрес добавлен в whitelist Namecheap
""")
    print("✅ README файл создан")
    
    # Создаем ZIP архив
    zip_path = 'DNSAutomator_Windows.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, arcname)
                print(f"📦 Добавлен в архив: {arcname}")
    
    # Очищаем временную папку
    shutil.rmtree(temp_dir)
    
    # Проверяем размер архива
    zip_size = os.path.getsize(zip_path)
    print(f"✅ ZIP архив создан: {zip_path}")
    print(f"📊 Размер архива: {zip_size:,} байт ({zip_size/1024/1024:.1f} MB)")
    
    return True

if __name__ == "__main__":
    success = create_windows_zip()
    if success:
        print("\n" + "="*60)
        print("🎉 WINDOWS ZIP АРХИВ ГОТОВ!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ ОШИБКА СОЗДАНИЯ АРХИВА")
        print("="*60)