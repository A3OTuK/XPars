import PyInstaller.__main__
import os

# Определение относительных путей к файлам
base_dir = os.path.dirname(os.path.abspath(__file__))

# Функция для добавления относительных путей к файлам
def add_data_target(source, target):
    source_path = os.path.join(base_dir, source)
    if not os.path.exists(source_path):
        print(f"Путь {source_path} не существует")
    return f"{source_path};{target}"

print("Начало сборки")
icon_path = os.path.join(base_dir, 'icon.ico')
if not os.path.exists(icon_path):
    print(f"Файл иконки по пути {icon_path} не найден")
else:
    print(f"Файл иконки найден по пути {icon_path}")
    PyInstaller.__main__.run([
        '--name', 'XPARSER',
        '--onefile',
        '--windowed',  # Используйте '--windowed', если вы не хотите видеть консольное окно
        '--add-data', add_data_target('debug.log', '.'),
        '--add-data', add_data_target('requirements.txt', '.'),
        '--icon', icon_path,  # Используем только путь к файлу иконки
        'main.py'  # Добавьте основной скрипт
    ])
print("Сборка завершена")
