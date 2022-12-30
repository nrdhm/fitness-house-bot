import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from .fh_scrape import scrape_fh_schedule

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

activities = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global activities
    current_activities = scrape_fh_schedule("now")
    next_activities = scrape_fh_schedule("next")
    if not next_activities:
        await update.message.reply_text(
            "Расписание на следующую неделю отсутствует.",
        )
    activities = current_activities + next_activities
    await update.message.reply_text(
        "Выбери дату:",
        reply_markup=await _schedule_buttons(),
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    if query.data == "back":
        await query.edit_message_text(
            "Выбери дату:",
            reply_markup=await _schedule_buttons(),
        )
        return

    if query.data == "-":
        return

    date = query.data
    chosen = [x for x in activities if x["date"] == date]
    assert chosen
    header = f"Расписание на {date}"
    body = [f'{x["time"]}: {x["name"]}' for x in chosen]
    await query.edit_message_text(
        text="\n".join([header, *body]),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Назад", callback_data="back")]],
        ),
    )


async def _schedule_buttons() -> InlineKeyboardMarkup:
    dates = sorted(
        set(x["date"] for x in activities),
        key=lambda x: tuple(reversed(x.split(",")[0].split("."))),
    )
    this_week, dates = dates[:7], dates[7:]
    next_week = ["-"] * 7
    if dates:
        next_week = dates[:7]
    keyboard = [
        [
            InlineKeyboardButton(this, callback_data=this),
            InlineKeyboardButton(next, callback_data=next),
        ]
        for this, next in zip(this_week, next_week)
    ]
    return InlineKeyboardMarkup(keyboard)


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=update.message.text
    )


async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_caps = " ".join(context.args).upper()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I didn't understand that command.",
    )
