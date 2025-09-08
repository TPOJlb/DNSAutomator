import os
import subprocess

def convert_png_to_icons():
    """Конвертирует PNG иконку в форматы для macOS и Windows"""
    if not os.path.exists('icon.png'):
        print("❌ Файл icon.png не найден!")
        return False
    
    print("🔄 Конвертация icon.png в иконки...")
    
    # Конвертация в .icns (macOS)
    if not os.path.exists('icons.icns'):
        try:
            print("📱 Создаем .icns для macOS...")
            os.makedirs('icon.iconset', exist_ok=True)
            
            sizes = [16, 32, 64, 128, 256, 512, 1024]
            for size in sizes:
                subprocess.run([
                    'sips', '-z', str(size), str(size),
                    'icon.png', '--out', f'icon.iconset/icon_{size}x{size}.png'
                ], check=True)
            
            subprocess.run(['iconutil', '-c', 'icns', 'icon.iconset'], check=True)
            subprocess.run(['rm', '-rf', 'icon.iconset'])
            print("✅ Создан icons.icns")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка создания .icns: {e}")
            return False
    
    # Конвертация в .ico (Windows)
    if not os.path.exists('icons.ico'):
        try:
            print("🪟 Создаем .ico для Windows...")
            # Создаем временную папку для иконок
            os.makedirs('ico_temp', exist_ok=True)
            
            # Создаем иконки разных размеров
            sizes = [16, 32, 48, 64, 128, 256]
            for size in sizes:
                subprocess.run([
                    'sips', '-z', str(size), str(size),
                    'icon.png', '--out', f'ico_temp/icon_{size}x{size}.png'
                ], check=True)
            
            # Собираем в .ico (просто копируем PNG, PyInstaller сам преобразует)
            subprocess.run(['cp', 'icon.png', 'icons.ico'])
            subprocess.run(['rm', '-rf', 'ico_temp'])
            print("✅ Создан icons.ico")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка создания .ico: {e}")
            return False
    
    return True

if __name__ == "__main__":
    convert_png_to_icons()