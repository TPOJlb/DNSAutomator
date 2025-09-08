#!/usr/bin/env python3
import os
import shutil
import zipfile

def finish_build():
    print("🎯 ЗАВЕРШЕНИЕ СБОРКИ WINDOWS EXE")
    
    # Проверяем что создалось
    if os.path.exists('dist/DNSAutomator'):
        # Переименовываем в EXE
        exe_path = 'dist/DNSAutomator.exe'
        os.rename('dist/DNSAutomator', exe_path)
        print(f"✅ Переименовано: dist/DNSAutomator → {exe_path}")
        
        # Проверяем размер
        file_size = os.path.getsize(exe_path)
        print(f"📊 Размер EXE: {file_size:,} байт ({file_size/1024/1024:.1f} MB)")
        
        # Создаем ZIP архив
        zip_path = 'DNSAutomator_Windows.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(exe_path, 'DNSAutomator.exe')
            if os.path.exists('config.json'):
                zipf.write('config.json', 'config.json')
                print("✅ Добавлен config.json в архив")
        
        print(f"📦 Создан ZIP архив: {zip_path}")
        
        return True
        
    elif os.path.exists('dist/DNSAutomator.exe'):
        print("✅ EXE файл уже создан: dist/DNSAutomator.exe")
        return True
        
    else:
        print("❌ EXE файл не найден")
        if os.path.exists('dist'):
            files = os.listdir('dist')
            print(f"📁 Содержимое dist: {files}")
        return False

if __name__ == "__main__":
    success = finish_build()
    if success:
        print("\n" + "="*60)
        print("🎉 WINDOWS EXE ГОТОВ!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ ЧТО-ТО ПОШЛО НЕ ТАК")
        print("="*60)