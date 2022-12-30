import logging
import os

from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler,
)

from .bot import (
    start,
    unknown,
    handle_choose_date,
    handle_date_chosen,
    CHOOSE_DATE,
    DATE_CHOSEN,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


if __name__ == "__main__":
    application = Application.builder().token(os.environ["TOKEN"]).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_DATE: [CallbackQueryHandler(handle_choose_date)],
            DATE_CHOSEN: [CallbackQueryHandler(handle_date_chosen)],
        },
        fallbacks=[unknown],
    )
    application.add_handler(conv_handler)
    application.run_polling()
