import shutil

import PyInstaller.__main__


def main():
    # Очистка предыдущих сборок
    shutil.rmtree('build', ignore_errors=True)
    shutil.rmtree('dist', ignore_errors=True)

    # Основные параметры сборки
    build_params = [
        '--name=XPARSER',
        '--onefile',
        '--windowed',
        '--add-data=debug.log;.',
        '--add-data=requirements.txt;.',
        '--icon=icon.ico',
        'main.py'
    ]

    # Запускаем сборку
    PyInstaller.__main__.run(build_params)

if __name__ == '__main__':
    main()