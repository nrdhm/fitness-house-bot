import requests
from bs4 import BeautifulSoup


urls = {
    "now": "https://www.fitnesshouse.ru/raspisanie-shavrova.html",
    "next": "https://www.fitnesshouse.ru/2915.html",
}


def scrape_fh_schedule(when: str) -> list:
    url = urls[when]
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "lxml")
    # Расписание находится в формате таблицы.
    # Представляем таблицу в виде списка строк.
    rows = soup.select("table.shedule tr")
    if not rows:
        return []
    # В первой строке находятся заголовки -- даты занятий.
    [_, *dates] = [y.text for y in rows[0].select("th")]
    # Это расписание на неделю, дат всего семь.
    assert len(dates) == 7
    activities = []
    last_time = None  # handle spanning multi-rows
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
        for date, cell in zip(dates, cells):
            x = _activity(last_time, date, cell)
            if x:
                activities.append(x)
    return activities


def _scrape_activity_cell(td_cell):
    # пустые ячейки без класса
    if not td_cell["class"]:
        return None
    # у детских занятий нет onclic атрибута
    if not td_cell.get("onclick"):
        return None
    [name_p] = td_cell.select("p.hdr")
    [trainer_p] = td_cell.select("p.trainer")
    [place_p] = td_cell.select("p.place")
    return {
        "name": name_p.text.strip(),
        "trainer": trainer_p.text.strip(),
        "place": place_p.text.strip(),
    }


def _activity(time, date, td_cell):
    if not (info := _scrape_activity_cell(td_cell)):
        return
    return {
        "time": time,
        "date": date,
        **info,
    }


if __name__ == "__main__":
    from pprint import pprint

    pprint(scrape_fh_schedule("now"))
