# Geodata Rules Checker

GitHub Actions workflow для проверки наличия всех используемых geosite/geoip правил в `.dat` файлах из [runetfreedom/russia-v2ray-rules-dat](https://github.com/runetfreedom/russia-v2ray-rules-dat).

## Как работает

1. **Скачивает** `geosite.dat` и `geoip.dat` из последнего релиза
2. **Парсит** protobuf-структуру файлов (без зависимости от `protoc` — используется runtime descriptor)
3. **Сверяет** список `country_code` тегов с нашим списком используемых правил
4. **Алерт** — при отсутствии тегов:
   - Workflow завершается с ошибкой
   - Создаётся GitHub Issue с лейблом `geodata-alert`
   - Пишется Job Summary в Actions

## Структура файлов

```
.github/workflows/check-geodata.yml   # GitHub Actions workflow
scripts/check_geodata.py               # Python-скрипт проверки
scripts/required_rules.json            # Конфиг: какие теги нужны в каких файлах
```

## Настройка

### 1. Скопируйте файлы в ваш репозиторий

Скопируйте все три файла, сохраняя структуру папок.

### 2. Отредактируйте `required_rules.json`

Добавьте или уберите теги, которые вы используете в конфигах xray/v2ray:

```json
{
  "geosite_files": {
    "geosite_RU.dat": {
      "url": "https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geosite.dat",
      "required_tags": [
        "ru-available-only-inside",
        "category-ru",
        "ru-blocked"
      ]
    }
  },
  "geoip_files": {
    "geoip_RU.dat": {
      "url": "https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geoip.dat",
      "required_tags": [
        "ru-blocked",
        "private"
      ]
    }
  }
}
```

### 3. Создайте лейбл `geodata-alert`

В Settings → Labels вашего репозитория создайте лейбл `geodata-alert` — он используется для Issue-алертов.

### 4. (Опционально) Добавьте другие geo-файлы

Формат поддерживает несколько файлов. Например, для Loyalsoldier:

```json
{
  "geosite_files": {
    "geosite_RU.dat": { "..." : "..." },
    "geosite_loyalsoldier.dat": {
      "url": "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat",
      "required_tags": ["google", "facebook", "telegram"]
    }
  }
}
```

## Расписание

Workflow запускается:
- **Каждые 6 часов** (по cron, синхронно с обновлениями upstream)
- **Вручную** через Actions → Run workflow
- **При push** изменений в скрипт или конфиг

## Локальный запуск

```bash
pip install protobuf
python scripts/check_geodata.py --config scripts/required_rules.json
```
