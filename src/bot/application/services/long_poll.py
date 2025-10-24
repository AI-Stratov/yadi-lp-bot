import asyncio
from datetime import datetime
from hashlib import sha256
import json

import aiohttp
from redis.exceptions import ConnectionError as RedisConnectionError
from bot.common.logs import logger
from bot.domain.entities.notification import NotificationTask
from bot.domain.services.long_poll import LongPollServiceInterface
from bot.common.utils.path_parser import (
    parse_datetime,
    build_public_file_url,
    extract_subject_from_path,
    extract_topic_from_path,
    extract_group_from_path,
    extract_group_raw_from_path,
    extract_teacher_from_filename,
    extract_date_from_filename,
    extract_date_from_path,
)


class YandexDiskPollingService(LongPollServiceInterface):
    async def start(self):
        """Запустить цикл опроса публичной папки Я.Диска."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop(), name="yadisk_poll")
        logger.info("✅ Опрос Яндекс.Диска запущен")

    async def stop(self):
        """Остановить цикл опроса и дождаться завершения фоновой задачи."""
        self._running = False
        if hasattr(self, "_task") and self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Опрос Яндекс.Диска остановлен")

    async def _poll_loop(self):
        """Основной цикл опроса: собирает новые файлы и отправляет задания в очередь."""
        while self._running:
            try:
                new_files = await self._check_for_new_files()
                if new_files:
                    logger.info(f"📨 Найдено новых файлов: {new_files}")
            except Exception as e:
                logger.exception(f"Ошибка опроса: {e}")

            await asyncio.sleep(self.poll_interval)

    async def _safe_redis_get(self, key: str) -> str | bytes | None:
        try:
            return await self.redis.get(key)
        except RedisConnectionError as e:
            logger.error(f"Redis недоступен при GET {key}: {e}")
            return None

    async def _safe_redis_set(self, key: str, value: str, *, ex: int | None = None) -> None:
        try:
            await self.redis.set(key, value, ex=ex)
        except RedisConnectionError as e:
            logger.error(f"Redis недоступен при SET {key}: {e}")

    async def _check_for_new_files(self) -> int:
        """Проверяет диск и добавляет новые файлы в очередь. Возвращает количество новых задач."""
        # Читаем чекпоинт - время последней проверки
        checkpoint_key = self._get_checkpoint_key()
        last_check = await self._safe_redis_get(checkpoint_key)
        last_check_dt = parse_datetime(last_check)

        # Запоминаем время начала текущего обхода (без timezone)
        current_check_dt = datetime.now()

        if last_check_dt:
            logger.info(f"🕒 Последняя проверка: {last_check_dt.isoformat()}")
        else:
            logger.info("🆕 Первый запуск, чекпоинта нет")

        # Собираем новые файлы и параллельно считаем статистику по группам
        new_tasks = []
        group_counts: dict[str, int] = {}
        common_count = 0

        async for file_dict in self._fetch_all_files():
            file_modified = parse_datetime(file_dict.get("modified"))

            # Подсчёт для статистики
            path = file_dict.get("path", "")
            g = extract_group_from_path(path)
            if g:
                group_name: str = str(g)  # StrEnum -> str
                group_counts[group_name] = group_counts.get(group_name, 0) + 1
            else:
                common_count += 1

            # Пропускаем старые файлы (модифицированные до последней проверки)
            if last_check_dt and file_modified and file_modified <= last_check_dt:
                continue

            # Создаём задачу на уведомление
            task = self._create_notification_task(file_dict)
            new_tasks.append(task)

        # Сохраняем задачи в очередь и обновляем чекпоинт
        if new_tasks:
            try:
                await self.notification_service.enqueue_many(new_tasks)
            except Exception as e:
                logger.error(f"Не удалось поставить задачи в очередь: {e}")
            await self._safe_redis_set(checkpoint_key, current_check_dt.isoformat())
            logger.info(f"✅ Чекпоинт обновлен: {current_check_dt.isoformat()}")
        elif last_check_dt:
            # Даже если файлов нет, обновляем чекпоинт
            await self._safe_redis_set(checkpoint_key, current_check_dt.isoformat())
            logger.debug("⏭️ Новых файлов нет, чекпоинт обновлен")

        # Обновляем кэш статистики по группам (5 минут)
        try:
            await self._save_group_counts_cache(group_counts, common_count, ttl=300)
        except Exception as e:
            logger.debug(f"Не удалось обновить кэш статистики групп: {e}")

        return len(new_tasks)

    async def _fetch_all_files(self):
        """Получает все файлы с диска (обходит директории рекурсивно)."""
        # Используем стек для обхода в ширину
        dirs_to_scan = [""]  # Начинаем с корня

        while dirs_to_scan:
            current_path = dirs_to_scan.pop(0)

            # Запрашиваем содержимое директории
            items = await self._fetch_directory(current_path)

            for item in items:
                if item.get("type") == "file":
                    yield item
                elif item.get("type") == "dir":
                    # Добавляем поддиректорию в очередь на обход
                    dirs_to_scan.append(item.get("path"))

    async def _fetch_directory(self, path: str) -> list[dict]:
        """Запрашивает содержимое одной директории (с пагинацией)."""
        all_items: list[dict] = []
        offset = 0
        limit = 200

        while True:
            params = {
                "public_key": self.public_root_url,
                "limit": limit,
                "offset": offset,
            }
            if path:
                params["path"] = path

            try:
                timeout = aiohttp.ClientTimeout(total=self.http_timeout)
                url = "https://cloud-api.yandex.net/v1/disk/public/resources"

                async with self.http.get(url, params=params, timeout=timeout) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    items = data.get("_embedded", {}).get("items", [])

                    if not items:
                        break

                    # добавляем полученные элементы
                    all_items.extend(items)

                    # Если получили меньше чем limit, значит это последняя страница
                    if len(items) < limit:
                        break

                    offset += limit
                    await asyncio.sleep(0.1)  # Небольшая пауза между запросами

            except Exception as e:
                logger.error(f"Ошибка запроса к Яндекс.Диску (path={path}): {e}")
                break

        return all_items

    def _create_notification_task(self, file_dict: dict) -> NotificationTask:
        """Создаёт задачу на уведомление из данных файла."""
        path = file_dict.get("path", "")
        file_name = file_dict.get("name", "")
        subject_code = extract_subject_from_path(path)
        study_group = extract_group_from_path(path)
        group_raw = extract_group_raw_from_path(path)
        topic = extract_topic_from_path(path)

        # Формируем прямую ссылку на просмотр файла на Яндекс.Диске
        public_url = build_public_file_url(path, self.public_root_url)

        # Парсим метаданные из названия файла/пути
        teacher = extract_teacher_from_filename(file_name)

        # Источник даты по приоритету: имя файла -> путь -> created -> modified
        lesson_date_source = None
        lesson_date = extract_date_from_filename(file_name)
        if lesson_date:
            lesson_date_source = "filename"
        else:
            lesson_date = extract_date_from_path(path)
            if lesson_date:
                lesson_date_source = "path"
            else:
                lesson_date = parse_datetime(file_dict.get("created"))
                if lesson_date:
                    lesson_date_source = "created"
                else:
                    lesson_date = parse_datetime(file_dict.get("modified"))
                    if lesson_date:
                        lesson_date_source = "modified"

        if lesson_date_source:
            logger.debug(
                "📅 lesson_date=%s (source=%s) file_name='%s' path='%s'",
                lesson_date.isoformat() if lesson_date else None,
                lesson_date_source,
                file_name,
                path,
            )
        else:
            logger.debug("📅 lesson_date not found in filename/path/created/modified for '%s'", file_name)

        return NotificationTask(
            subject_code=subject_code,
            subject_title=None,
            topic=topic,
            study_group=study_group,
            group_raw=group_raw,
            teacher=teacher,
            lesson_date=lesson_date,
            file_name=file_name,
            file_path=path,
            public_url=public_url,
            download_url=file_dict.get("file"),  # Временная ссылка для скачивания
            md5=file_dict.get("md5"),
            resource_id=file_dict.get("resource_id"),
            modified_iso=file_dict.get("modified"),
        )

    def _get_checkpoint_key(self) -> str:
        """Генерирует ключ Redis для хранения чекпоинта."""
        url_hash = sha256(self.public_root_url.encode()).hexdigest()[:12]
        base = f"checkpoint:{url_hash}"
        return f"{self.key_prefix}:{base}" if getattr(self, 'key_prefix', None) else base

    def _group_counts_cache_key(self) -> str:
        url_hash = sha256(self.public_root_url.encode()).hexdigest()[:12]
        base = f"stats:group_counts:{url_hash}"
        return f"{self.key_prefix}:{base}" if getattr(self, 'key_prefix', None) else base

    async def _save_group_counts_cache(self, groups: dict[str, int], common: int, ttl: int = 300) -> None:
        payload = {
            "groups": groups,
            "common": common,
            "computed_at": datetime.now().isoformat(),
        }
        await self._safe_redis_set(self._group_counts_cache_key(), json.dumps(payload), ex=ttl)
