import logging
import os
from itertools import groupby, zip_longest

from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

from .fh_scrape import ActivitySchedule, scrape_fh_schedule

logging.basicConfig(
    format="%(asctime)s - %(name)s:%(funcName)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


CHOOSE_DATE, DATE_CHOSEN = range(2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить расписание занятий на две недели и показать его в виде кнопок."""
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)
    # получить расписание на эту и следующую недели
    this_week = await scrape_fh_schedule("now")
    next_week = await scrape_fh_schedule("next")
    # сохранить их в контексте
    context.bot_data["this_week"] = this_week
    context.bot_data["next_week"] = next_week
    if not next_week:
        await update.message.reply_text("Нет расписания на следующую неделю.")
    # вывести две колонки кнопок с расписанием
    await update.message.reply_text(
        "Выбери дату:",
        reply_markup=await _build_choose_dates_keyboard(this_week, next_week),
    )
    return CHOOSE_DATE


async def handle_choose_date(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Обработка нажатия на кнопку с занятиями на день.
    Показать расписание на выбранный день и кнопки назад, завтра, вчера.
    """
    # тут формальности общения с сервером телеги
    query = update.callback_query
    await query.answer()
    await _show_activities_for_date(update.callback_query, context)
    return DATE_CHOSEN


async def handle_date_chosen(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Обработка нажатия на кнопки назад, завтра, вчера."""
    # тут формальности общения с сервером телеги
    query = update.callback_query
    await query.answer()

    this_week: ActivitySchedule = context.bot_data["this_week"]
    next_week: ActivitySchedule = context.bot_data["next_week"]

    logger.info("User %s chose %s.", query.from_user.first_name, query.data)

    if query.data == "back":
        await query.edit_message_text(
            "Выбери дату:",
            reply_markup=await _build_choose_dates_keyboard(this_week, next_week),
        )
        return CHOOSE_DATE
    if query.data.startswith("this_week") or query.data.startswith("next_week"):
        await _show_activities_for_date(update.callback_query, context)
    return DATE_CHOSEN


async def _build_choose_dates_keyboard(
    this_week: ActivitySchedule, next_week: ActivitySchedule
) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(this_date, callback_data=f"this_week {this_date}"),
            InlineKeyboardButton(next_date, callback_data=f"next_week {next_date}"),
        ]
        for this_date, next_date in zip_longest(this_week, next_week, fillvalue="-")
    ]
    return InlineKeyboardMarkup(keyboard)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    return ConversationHandler.END


async def _show_activities_for_date(
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE
) -> None:
    # логируем юзера
    logger.info("User %s chose %s.", query.from_user.first_name, query.data)
    # В query.data может находится только строка.
    # Поэтому там сохраняем что-то вроде "now 02.01, пн"
    # где now указывает на эту либо следующую (next) неделю
    key, date = query.data.split(" ", maxsplit=1)
    # Даты нет -- нет расписания. Нужно выбрать другую дату.
    if date == "-":
        return CHOOSE_DATE
    # Получаем занятия на выбранную дату из контекста.
    schedule: ActivitySchedule = context.bot_data[key]
    activities = schedule[date]
    assert activities
    # Находим следующую и предыдщую даты.
    prev_date, next_date = _find_neighbour_dates(
        list(schedule.keys()),
        date,
    )
    # Готовим ответ.
    header = f"Занятия на {date}"
    keyboard = []
    for time, activities in groupby(activities, key=lambda x: x["time"]):
        for activity in activities:
            color = ""
            if "yellow" in activity["css_class"]:
                color = "🟡"
            if "blue" in activity["css_class"]:
                color = "🔵"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f'{time} – {activity["name"]} {color}', callback_data="-"
                    )
                ]
            )
    keyboard.append(
        [InlineKeyboardButton(" --- ", callback_data="-")],
    )
    keyboard.append(
        [InlineKeyboardButton("↶ Назад", callback_data="back")],
    )
    dates_buttons = []
    if prev_date != date:
        dates_buttons.append(
            InlineKeyboardButton(f"⇐ {prev_date}", callback_data=f"{key} {prev_date}")
        )
    if next_date != date:
        dates_buttons.append(
            InlineKeyboardButton(f"{next_date} ⇒", callback_data=f"{key} {next_date}")
        )
    keyboard.append(dates_buttons)
    await query.edit_message_text(
        text=header,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )


def _find_neighbour_dates(days: list[str], date: str) -> tuple[str, str]:
    assert date in days
    idx = days.index(date)
    prev_idx = max(0, idx - 1)
    next_idx = min(len(days) - 1, idx + 1)
    return days[prev_idx], days[next_idx]


def main() -> None:
    """Run the bot."""
    application = Application.builder().token(os.environ["TOKEN"]).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_DATE: [CallbackQueryHandler(handle_choose_date)],
            DATE_CHOSEN: [CallbackQueryHandler(handle_date_chosen)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    application.run_polling()
