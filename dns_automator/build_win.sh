#!/bin/bash
APP_NAME="dns_automator"
MAIN_SCRIPT="app.py"

mkdir -p build

docker run --rm -v "$(pwd)":/src ghcr.io/cdrx/pyinstaller-windows:python3.11 /bin/bash -c "
    pip install --upgrade pip setuptools wheel
    pip install pyarmor requests gspread oauth2client
    pyinstaller --onefile /src/$MAIN_SCRIPT --name $APP_NAME --distpath /src/build
"

echo "✅ Сборка завершена! Файл: build/$APP_NAME.exe"
