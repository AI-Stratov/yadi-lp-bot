from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import LinkPreviewOptions
from aiogram.exceptions import TelegramBadRequest
from dishka import FromDishka
from dishka.integrations.aiogram import inject
from redis.asyncio import Redis

from bot.application.services.long_poll import YandexDiskPollingService
from bot.domain.services.scheduler import SchedulerServiceInterface
from bot.application.widgets.keyboards import build_stats_menu_kb, build_kv_list_kb
from bot.common.utils.formatters import StatisticsFormatter
from bot.common.utils.formatting import parse_dt_raw, fmt_secs, fmt_int, human_ago
from bot.common.utils.permissions import is_admin
from bot.domain.entities.user import CreateUserEntity
from bot.domain.services.statistics import StatisticsServiceInterface
from bot.domain.services.user import UserServiceInterface

router = Router(name="stats")


@router.message(Command("stats"))
@inject
async def cmd_stats(
    message: types.Message,
    user_service: FromDishka[UserServiceInterface],
    stats_service: FromDishka[StatisticsServiceInterface],
):
    """Показать общую статистику (только для администраторов)."""
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(message.from_user))
    if not is_admin(caller):
        await message.answer("🚫 Доступно только администраторам")
        return

    snap = await stats_service.build_snapshot()
    text = StatisticsFormatter.format_summary(snap)

    await message.answer(
        text,
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        reply_markup=build_stats_menu_kb(),
    )


@router.callback_query(F.data == "stats:refresh")
@inject
async def cb_stats_refresh(
    callback: types.CallbackQuery,
    user_service: FromDishka[UserServiceInterface],
    stats_service: FromDishka[StatisticsServiceInterface],
):
    """Обновить статистику."""
    await callback.answer()
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(callback.from_user))
    if not is_admin(caller):
        return

    snap = await stats_service.build_snapshot()
    text = StatisticsFormatter.format_summary(snap)

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=build_stats_menu_kb(),
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise


@router.callback_query(F.data == "stats:disabled")
@inject
async def cb_stats_disabled(
    callback: types.CallbackQuery,
    user_service: FromDishka[UserServiceInterface],
    stats_service: FromDishka[StatisticsServiceInterface],
):
    await callback.answer()
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(callback.from_user))
    if not is_admin(caller):
        return
    snap = await stats_service.build_snapshot()
    items = list(snap.top_excluded.items()) if getattr(snap, "top_excluded", None) else []
    kb = build_kv_list_kb(items=items, page=0, back_cb="stats:refresh", page_cb_prefix="stats:disabled:page")
    await callback.message.edit_text("🚫 Отключённые дисциплины (топ)", reply_markup=kb)


@router.callback_query(F.data.startswith("stats:disabled:page:"))
@inject
async def cb_stats_disabled_page(
    callback: types.CallbackQuery,
    user_service: FromDishka[UserServiceInterface],
    stats_service: FromDishka[StatisticsServiceInterface],
):
    await callback.answer()
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(callback.from_user))
    if not is_admin(caller):
        return
    try:
        page = int(callback.data.rsplit(":", 1)[1])
    except Exception:
        page = 0
    snap = await stats_service.build_snapshot()
    items = list(snap.top_excluded.items()) if getattr(snap, "top_excluded", None) else []
    kb = build_kv_list_kb(items=items, page=page, back_cb="stats:refresh", page_cb_prefix="stats:disabled:page")
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise


@router.callback_query(F.data.startswith("stats:courses:page:"))
@inject
async def cb_stats_courses(
    callback: types.CallbackQuery,
    user_service: FromDishka[UserServiceInterface],
    stats_service: FromDishka[StatisticsServiceInterface],
):
    await callback.answer()
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(callback.from_user))
    if not is_admin(caller):
        return
    try:
        page = int(callback.data.rsplit(":", 1)[1])
    except Exception:
        page = 0
    snap = await stats_service.build_snapshot()
    items = sorted(list(snap.by_course.items()), key=lambda kv: (-(kv[1]), kv[0]))
    kb = build_kv_list_kb(items=items, page=page, back_cb="stats:refresh", page_cb_prefix="stats:courses:page")
    try:
        await callback.message.edit_text("📚 Пользователи по курсам", reply_markup=kb)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise


@router.callback_query(F.data.startswith("stats:groups:page:"))
@inject
async def cb_stats_groups(
    callback: types.CallbackQuery,
    user_service: FromDishka[UserServiceInterface],
    stats_service: FromDishka[StatisticsServiceInterface],
):
    await callback.answer()
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(callback.from_user))
    if not is_admin(caller):
        return
    try:
        page = int(callback.data.rsplit(":", 1)[1])
    except Exception:
        page = 0
    snap = await stats_service.build_snapshot()
    items = sorted(list(snap.by_group.items()), key=lambda kv: (-(kv[1]), kv[0]))
    kb = build_kv_list_kb(items=items, page=page, back_cb="stats:refresh", page_cb_prefix="stats:groups:page")
    try:
        await callback.message.edit_text("👥 Пользователи по группам", reply_markup=kb)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise


@router.callback_query(F.data == "stats:nop")
async def cb_stats_nop(callback: types.CallbackQuery):
    await callback.answer()


@router.message(Command("status"))
@inject
async def cmd_status(
    message: types.Message,
    user_service: FromDishka[UserServiceInterface],
    redis: FromDishka[Redis],
    polling: FromDishka[YandexDiskPollingService],
    scheduler: FromDishka[SchedulerServiceInterface],
    stats_service: FromDishka[StatisticsServiceInterface],
):
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(message.from_user))
    if not is_admin(caller):
        await message.answer("🚫 Доступно только администраторам")
        return

    # Чекпоинт long-poll
    try:
        checkpoint_raw = await redis.get(polling._get_checkpoint_key())  # noqa: SLF001
        checkpoint_dt = parse_dt_raw(checkpoint_raw)
        checkpoint = checkpoint_dt.strftime("%d.%m.%Y %H:%M:%S") if checkpoint_dt else "—"
        checkpoint_ago = human_ago(checkpoint_dt)
    except Exception:
        checkpoint = "—"
        checkpoint_ago = "—"

    # Общая информация по long-poll
    poll_url = getattr(polling, "public_root_url", "—")
    poll_interval = fmt_secs(getattr(polling, "poll_interval", "—"))
    http_timeout = fmt_secs(getattr(polling, "http_timeout", "—"))
    poll_running = getattr(polling, "_running", False)

    # Планировщик
    sched_interval = fmt_secs(getattr(scheduler, "check_interval", "—"))
    sched_running = getattr(scheduler, "_running", False)

    # Очереди/план через сервис статистики
    snap = await stats_service.build_snapshot()
    queue_len = snap.queue_len
    scheduled_total = snap.scheduled_total

    lines: list[str] = ["ℹ️ <b>Статус сервиса</b>", "🛰️ <b>Long‑poll</b>"]

    # Long-poll
    if poll_url and poll_url != "—":
        lines.append(f"  • URL: <a href=\"{poll_url}\">{poll_url}</a>")
    else:
        lines.append(f"  • URL: {poll_url}")
    lines.append(f"  • Интервал опроса: {poll_interval}")
    lines.append(f"  • HTTP таймаут: {http_timeout}")
    lines.append(f"  • Состояние: {'<b>работает</b>' if poll_running else '<b>остановлен</b>'}")
    lines.append(f"  • Последняя проверка: {checkpoint} ({checkpoint_ago})")

    # Scheduler
    lines.append("⏰ <b>Планировщик уведомлений</b>")
    lines.append(f"  • Период проверки: {sched_interval}")
    lines.append(f"  • Состояние: {'<b>работает</b>' if sched_running else '<b>остановлен</b>'}")

    # Queues
    lines.append("🗃️ <b>Очереди</b>")
    lines.append(f"  • Входящих задач: <b>{fmt_int(queue_len)}</b>")
    lines.append(f"  • Запланировано к отправке: <b>{fmt_int(scheduled_total)}</b>")

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
