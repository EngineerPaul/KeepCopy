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

На Windows при установке Python из Microsoft Store задайте короткий путь кэша Nuitka (скрипт `build_exe.py` делает это автоматически):

```powershell
$env:NUITKA_CACHE_DIR = "C:\NuitkaCache"
```

Без этого MinGW из кэша может не найти `windows.h` из‑за длинного пути в `%LOCALAPPDATA%`.

### Сборка одной командой

```bash
python scripts/build_exe.py
```

Скрипт при необходимости создаёт `assets/keepcopy_icon.ico` и запускает Nuitka. Или...

```bash
python scripts/pack_dist.py
```

`pack_dist.py` собирает `compiler/KeepCopy.zip` без `settings.json`, `backup.log` и `errors/`.

### Результат

| Путь | Описание |
|------|----------|
| `compiler/KeepCopy.dist/` | Папка для распространения (все DLL и ресурсы) |
| `compiler/KeepCopy.dist/KeepCopy.exe` | Исполняемый файл |
| `compiler/KeepCopy.dist/assets/` | Иконки и прочие ресурсы |
| `compiler/KeepCopy.zip` | Архив папки `KeepCopy.dist` без `settings.json` |

Скопируйте **всю** папку `KeepCopy.dist` в постоянное место (например, `C:\Program Files\KeepCopy\`).  
Рядом с `KeepCopy.exe` создаются `settings.json`, `backup.log`, папка `errors/`.

Папку `compiler/` можно удалить и пересобрать в любой момент.

### Антивирус и Windows Defender

Скомпилированный `KeepCopy.exe` (Nuitka, standalone) **может ложно определяться** антивирусом или Windows Defender как угроза — например, `Trojan:Win32/Bearfoos.A!ml`. Суффикс `!ml` означает эвристику (машинное обучение), а не подтверждённый вирус. Так бывает у неподписанных exe, собранных из Python/Qt, особенно с автозапуском и фоновым режимом.

**Что сделать:**

1. Если файл попал в карантин — **восстановите** его в «Безопасность Windows» → «Журнал защиты».
2. Добавьте в **исключения** папку, где лежит приложение (всю `KeepCopy.dist`, а не только exe):
   - **Параметры** → **Конфиденциальность и защита** → **Безопасность Windows** → **Защита от вирусов и угроз** → **Управление настройками** → **Исключения** → **Добавить исключение** → **Папка**.
   - Укажите каталог с `KeepCopy.exe`, например `compiler\KeepCopy.dist` или постоянное место установки (`C:\Program Files\KeepCopy\`).
3. После переноса или пересборки обновите исключение на новый путь.

Для распространения другим пользователям желательна **цифровая подпись** exe; при ложном срабатывании можно отправить файл как ложноположительный: https://www.microsoft.com/wdsi/filesubmission

### Ручная сборка (эквивалент скрипта)

```bash
python scripts/build_icon.py
python -m nuitka ^
  --standalone ^
  --windows-console-mode=disable ^
  --assume-yes-for-downloads ^
  --enable-plugin=pyside6 ^
  --include-package=pathspec ^
  --include-data-dir=assets=assets ^
  --output-dir=compiler ^
  --output-filename=KeepCopy.exe ^
  --company-name=KeepCopy ^
  --product-name=KeepCopy ^
  --file-version=1.0.0 ^
  --windows-icon-from-ico=assets/keepcopy_icon.ico ^
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
| Имя файла | `KeepCopy.lnk` |
| Цель (exe) | `KeepCopy.exe` из папки сборки |
| Аргументы | `--background` |
| Режим окна ярлыка | Свернуто (WindowStyle = 7) |

В режиме разработки (без exe) ярлык указывает на `pythonw.exe` и `main.py --background`.

### Фоновый запуск (`--background`)

При автозапуске программа **не открывает окно** и **не появляется на основной панели задач**:

- окно создаётся, но остаётся скрытым;
- в трее (область уведомлений, «стрелочка» справа внизу) появляется иконка **KeepCopy**;
- двойной щелчок по иконке или пункт меню **«Открыть»** — показать окно;
- **«Выход»** — завершить программу;
- кнопка закрытия окна (×) в фоновом режиме **сворачивает в трей**, а не завершает приложение.

Обычный запуск (двойной щелчок по exe **без** `--background`) — окно открывается сразу, иконка на панели задач. Это нормальное поведение: фоновый режим только при автозапуске или явном `KeepCopy.exe --background`.

### Включение и выключение

1. **Через настройки** — чекбокс «Автозапуск при старте системы» → **Применить**.
2. **Вручную** — создать или удалить ярлык `KeepCopy.lnk` в `shell:startup` с аргументом `--background`.

При старте приложение сверяет галочку в `settings.json` с наличием ярлыка и при расхождении восстанавливает ярлык.

### Ограничения

- Только **Windows**; на других ОС автозапуск не настраивается.
- Нужна доступность **системного трея** (на части конфигураций может быть отключён).
- Путь в ярлыке **абсолютный**: после переноса папки с exe нужно пересоздать автозапуск (выкл. → вкл. в настройках).

## Иконка

- Исходник: `assets/keepcopy_icon.svg`
- Для exe: `python scripts/build_icon.py` → `assets/keepcopy_icon.ico`
- В окне и в трее: загрузка из SVG (`ui/app_icon.py`)

## Проверка сборки

Тестируйте `KeepCopy.exe` на машине **без** установленного Python.
