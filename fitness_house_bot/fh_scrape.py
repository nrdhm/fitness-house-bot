import io
import logging
import tokenize
from typing import TypedDict

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(
    format="%(asctime)s - %(name)s:%(funcName)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


urls = {
    "now": "https://www.fitnesshouse.ru/raspisanie-shavrova.html",
    "next": "https://www.fitnesshouse.ru/2915.html",
}


class BaseInfo(TypedDict):
    name: str
    trainer: str
    place: str
    css_class: list[str]
    description: str


class Activity(BaseInfo):
    time: str  # like '11.00'
    date: str  # like '31.12, сб'


ActivitySchedule = dict[str, list[Activity]]


async def scrape_fh_schedule(when: str) -> ActivitySchedule:
    url = urls[when]
    async with httpx.AsyncClient() as client:
        # Не показывать детские занятия.
        await client.post(url, data={"ScheduleFilter[nochild][0]": "0"})
        response = await client.get(url)
    soup = BeautifulSoup(response.text, "lxml")
    # Расписание находится в формате таблицы.
    # Представляем таблицу в виде списка строк.
    rows = soup.select("table.shedule tr")
    activities = {}
    if not rows:
        return activities
    dates: list[str]
    # В первой строке находятся заголовки -- даты занятий.
    [_, *dates] = [y.text for y in rows[0].select("th")]
    # Это расписание на неделю, дат всего семь.
    assert len(dates) == 7
    last_time = None
    for row in rows[1:]:
        # В каждой ячейке строки указаны занятия.
        cells = row.select("td")
        # Каждой строке соответствует время занятия.
        # Оно указано в первой ячейке строки
        if len(cells) != 7:
            [time_td, *cells] = cells
            last_time = time_td.text.strip()
        # либо его нет и время равно времени предыдущей строки.
        assert len(cells) == 7
        assert last_time
        # Сопоставляем каждой ячейке занятия дату.
        for date, cell in zip(dates, cells):
            activities.setdefault(date, [])
            x = _activity(last_time, date, cell)
            if x:
                activities[date].append(x)
    return activities


def _scrape_activity_cell(td_cell) -> BaseInfo:
    # пустые ячейки без класса
    if not td_cell["class"]:
        return None
    description = ""
    if onclick := td_cell.get("onclick"):
        description = _read_description_from_onclick(onclick)
    [name_p] = td_cell.select("p.hdr")
    [trainer_p] = td_cell.select("p.trainer")
    [place_p] = td_cell.select("p.place")
    return {
        "name": name_p.text.strip(),
        "trainer": trainer_p.text.strip(),
        "place": place_p.text.strip(),
        "css_class": td_cell["class"],
        "description": description,
    }


def _activity(time: str, date: str, td_cell) -> Activity:
    if not (info := _scrape_activity_cell(td_cell)):
        return
    return {
        "time": time,
        "date": date,
        **info,
    }


def _read_description_from_onclick(onclick: str) -> str:
    tokens = tokenize.generate_tokens(io.StringIO(onclick).readline)
    func_name, lpar, activity, comma, description, *rest = tokens
    if (
        func_name.string != "showShedulePopup"
        or lpar.string != "("
        or not activity.string
        or comma.string != ","
    ):
        logger.error("onclick tokenize failed: %s", onclick)
        return ""
    return description.string.strip("'")


if __name__ == "__main__":
    import asyncio
    from pprint import pprint

    async def main():
        pprint(await scrape_fh_schedule("now"))

    asyncio.run(main())
