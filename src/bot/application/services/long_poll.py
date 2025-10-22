import asyncio
from datetime import datetime
from hashlib import sha256
from typing import Any, Optional

import aiohttp
from bot.common.logs import logger
from bot.domain.entities.notification import NotificationTask
from bot.domain.services.long_poll import LongPollServiceInterface


class YandexDiskPollingService(LongPollServiceInterface):
    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop(), name="yadisk_poll")
        logger.info("✅ Опрос Яндекс.Диска запущен")

    async def stop(self):
        self._running = False
        if hasattr(self, "_task"):
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Опрос Яндекс.Диска остановлен")

    async def _poll_loop(self):
        """Основной цикл опроса."""
        while self._running:
            try:
                new_files = await self._check_for_new_files()
                if new_files:
                    logger.info(f"📨 Найдено новых файлов: {new_files}")
            except Exception as e:
                logger.exception(f"Ошибка опроса: {e}")

            await asyncio.sleep(self.poll_interval)

    async def _check_for_new_files(self) -> int:
        """Проверяет диск и добавляет новые файлы в очередь."""
        # Читаем чекпоинт - когда последний раз проверяли
        checkpoint_key = self._get_checkpoint_key()
        last_check = await self.redis.get(checkpoint_key)
        last_check_dt = self._parse_datetime(last_check)

        # Собираем новые файлы
        new_tasks = []
        newest_dt = last_check_dt

        async for file_dict in self._fetch_all_files():
            file_modified = self._parse_datetime(file_dict.get("modified"))

            # Пропускаем старые файлы
            if last_check_dt and file_modified <= last_check_dt:
                continue

            # Создаём задачу на уведомление
            task = self._create_notification_task(file_dict)
            new_tasks.append(task)

            # Отслеживаем самую новую дату
            if not newest_dt or file_modified > newest_dt:
                newest_dt = file_modified

        # Сохраняем задачи в очередь
        if new_tasks:
            await self.notification_service.enqueue_many(new_tasks)
            await self.redis.set(checkpoint_key, newest_dt.isoformat())

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
        all_items = []
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

                    all_items.extend(items)

                    # Если получили меньше чем limit, значит это последняя страница
                    if len(items) < limit:
                        break

                    offset += limit
                    await asyncio.sleep(0.05)  # Небольшая пауза между запросами

            except Exception as e:
                logger.error(f"Ошибка запроса к Яндекс.Диску (path={path}): {e}")
                break

        return all_items

    def _create_notification_task(self, file_dict: dict) -> NotificationTask:
        """Создаёт задачу на уведомление из данных файла."""
        path = file_dict.get("path", "")
        subject_code = self._extract_subject_from_path(path)

        return NotificationTask(
            subject_code=subject_code,
            subject_title=None,
            file_name=file_dict.get("name", ""),
            file_path=path,
            download_url=file_dict.get("file"),
            md5=file_dict.get("md5"),
            resource_id=file_dict.get("resource_id"),
            modified_iso=file_dict.get("modified"),
        )

    def _extract_subject_from_path(self, path: str) -> Optional[str]:
        """Извлекает код предмета из пути (ищет в сегментах пути)."""
        try:
            from bot.domain.entities.mappings import SUBJECTS

            # Разбиваем путь на сегменты и ищем известный предмет
            segments = [s for s in path.replace("\\", "/").split("/") if s]
            for segment in reversed(segments):
                if segment in SUBJECTS:
                    return segment
        except Exception:
            pass

        return None

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Парсит datetime из строки или bytes."""
        if not value:
            return None

        if isinstance(value, (bytes, bytearray)):
            value = value.decode()

        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    def _get_checkpoint_key(self) -> str:
        """Генерирует ключ Redis для хранения чекпоинта."""
        url_hash = sha256(self.public_root_url.encode()).hexdigest()[:12]
        return f"yadi-lp:checkpoint:{url_hash}"
