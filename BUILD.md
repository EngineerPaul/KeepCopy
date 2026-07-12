# Сборка и автозапуск

## Компиляция (Nuitka)

Результат сборки попадает в папку **`compiler/`** в корне проекта.

### Подготовка

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install nuitka ordered-set zstandard
```

### Сборка одной командой

```bash
python scripts/build_exe.py
```

Скрипт при необходимости создаёт `assets/archiver_icon.ico` и запускает Nuitka.

### Результат

| Путь | Описание |
|------|----------|
| `compiler/Archiver.dist/` | Папка для распространения (все DLL и ресурсы) |
| `compiler/Archiver.dist/Archiver.exe` | Исполняемый файл |
| `compiler/Archiver.dist/assets/` | Иконки и прочие ресурсы |

Скопируйте **всю** папку `Archiver.dist` в постоянное место (например, `C:\Program Files\Archiver\`).  
Рядом с `Archiver.exe` создаются `settings.json`, `backup.log`, папка `errors/`.

Папку `compiler/` можно удалить и пересобрать в любой момент.

### Ручная сборка (эквивалент скрипта)

```bash
python scripts/build_icon.py
python -m nuitka ^
  --standalone ^
  --windows-disable-console ^
  --enable-plugin=pyside6 ^
  --include-package=pathspec ^
  --include-data-dir=assets=assets ^
  --output-dir=compiler ^
  --output-filename=Archiver.exe ^
  --company-name=Archiver ^
  --product-name=Архиватор ^
  --file-version=1.0.0 ^
  --windows-icon-from-ico=assets/archiver_icon.ico ^
  main.py
```

## Автозапуск при старте Windows

Реализовано в `services/autostart.py`. При включении галочки в настройках создаётся ярлык в папке автозагрузки текущего пользователя; при выключении — удаляется.

### Где лежит папка автозагрузки

На всех современных Windows (7, 8, 10, 11) для текущего пользователя:

```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
```

Открыть в проводнике: `Win+R` → `shell:startup`.

В русской Windows папка в проводнике может называться **«Автозагрузка»**, но путь на диске с сегментами `Start Menu\Programs\Startup` одинаков.

### Ярлык

| Параметр | Значение |
|----------|----------|
| Имя файла | `Archiver.lnk` |
| Цель (exe) | `Archiver.exe` из папки сборки |
| Аргументы | `--background` |
| Режим окна ярлыка | Свернуто (WindowStyle = 7) |

В режиме разработки (без exe) ярлык указывает на `pythonw.exe` и `main.py --background`.

### Фоновый запуск (`--background`)

При автозапуске программа **не открывает окно** и **не появляется на основной панели задач**:

- окно создаётся, но остаётся скрытым;
- в трее (область уведомлений, «стрелочка» справа внизу) появляется иконка **Архиватор**;
- двойной щелчок по иконке или пункт меню **«Открыть»** — показать окно;
- **«Выход»** — завершить программу;
- кнопка закрытия окна (×) в фоновом режиме **сворачивает в трей**, а не завершает приложение.

Обычный запуск (двойной щелчок по exe **без** `--background`) — окно открывается сразу, иконка на панели задач.

### Включение и выключение

1. **Через настройки** — чекбокс «Автозапуск при старте системы» → **Применить**.
2. **Вручную** — создать или удалить ярлык `Archiver.lnk` в `shell:startup` с аргументом `--background`.

При старте приложение сверяет галочку в `settings.json` с наличием ярлыка и при расхождении восстанавливает ярлык.

### Ограничения

- Только **Windows**; на других ОС автозапуск не настраивается.
- Нужна доступность **системного трея** (на части конфигураций может быть отключён).
- Путь в ярлыке **абсолютный**: после переноса папки с exe нужно пересоздать автозапуск (выкл. → вкл. в настройках).

## Иконка

- Исходник: `assets/archiver_icon.svg`
- Для exe: `python scripts/build_icon.py` → `assets/archiver_icon.ico`
- В окне и в трее: загрузка из SVG (`ui/app_icon.py`)

## Проверка сборки

Тестируйте `Archiver.exe` на машине **без** установленного Python.
