import logging
from itertools import zip_longest

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from .fh_scrape import ActivitySchedule, scrape_fh_schedule

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


CHOOSE_DATE, DATE_CHOSEN = range(2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)
    this_week = scrape_fh_schedule("now")
    next_week = scrape_fh_schedule("next")
    context.bot_data["this_week"] = this_week
    context.bot_data["next_week"] = next_week
    if not next_week:
        await update.message.reply_text("Расписание на следующую неделю отсутствует.")
    await update.message.reply_text(
        "Выбери дату:",
        reply_markup=await _build_choose_dates_keyboard(this_week, next_week),
    )
    return CHOOSE_DATE


async def handle_choose_date(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()
    user = update.callback_query.from_user
    logger.info("User %s chose %s.", user.first_name, query.data)

    key, date = query.data.split(" ", maxsplit=1)
    if date == "-":
        return CHOOSE_DATE

    chosen = context.bot_data[key][date]
    assert chosen
    header = f"Расписание на {date}"
    body = [f'{x["time"]}: {x["name"]}' for x in chosen]
    await query.edit_message_text(
        text="\n".join([header, *body]),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Назад", callback_data="back")]],
        ),
    )
    return DATE_CHOSEN


async def handle_date_chosen(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()

    this_week = context.bot_data["this_week"]
    next_week = context.bot_data["next_week"]

    user = update.callback_query.from_user
    logger.info("User %s chose %s.", user.first_name, query.data)

    if query.data == "back":
        await query.edit_message_text(
            "Выбери дату:",
            reply_markup=await _build_choose_dates_keyboard(this_week, next_week),
        )
        return CHOOSE_DATE
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
