# Yandex Disk Lecture Notifications Bot (Проект)

Telegram‑бот, который отслеживает новые записи на Яндекс.Диске и присылает уведомления студентам.

## Команды

Доступно всем пользователям:

- /set — выбрать свой курс и группу (мастер настройки)
- /settings — настройки уведомлений (режим, время, исключить предметы)
- /help — показать справку по командам

Команды для администраторов:

- /stats — общая статистика сервиса
- /status — статус сервисов (long‑poll, планировщик, очереди)

Команда для суперпользователя:

- /roles — управление ролями пользователей

Всего содержательных команд: 5 основных пользовательских/админских (/set, /settings, /stats, /status) + служебная
/roles для суперпользователя.

## Требования

- Python 3.13+
- Redis (используется как хранилище состояний и очередей)

Рекомендуется использовать пакетный менеджер uv для запуска.

## Быстрый старт

1) Подготовьте .env в корне проекта (рядом с pyproject.toml):

```
# Telegram
TOKEN=123456:telegram-bot-token
SUPERUSER_ID=123456789

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_KEY_PREFIX=yadi-lp

# Yandex.Disk
PUBLIC_ROOT_URL=https://disk.yandex.ru/client/public/....
POLL_INTERVAL=600
HTTP_TIMEOUT=10.0

# Notifications
NOTIFICATION_CHECK_INTERVAL=300
```

2) Установите зависимости и запустите бота:

```
uv sync
uv run yadi-lp
```

Бот запускается с entry‑point `yadi-lp = bot.main:run` (см. [pyproject.toml]).

## Docker

```
docker build -t yadi-lp .
docker run --env-file .env yadi-lp
```

#### Некоторые файлы и папки имеют особую структуру, которая не очевидно парсится, поэтому файлы, лежащие в корне курса и нестандартные файлы игнорируются ботом

###### Спасибо [@Tishka17](https://github.com/Tishka17/tgbot_template) за шаблон проекта (хоть и сильно изменённый)
