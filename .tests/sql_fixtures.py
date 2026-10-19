from __future__ import annotations

from dataclasses import dataclass


WIDTHS = {"library_1": 1, "library_2": 2, "library_3": 1,
          "library_4": 2, "library_5": 2, "train_1": 5, "train_2": 5}


@dataclass
class Dataset:
    name: str
    sql: str
    expected: dict[str, list[tuple[str, ...]]]


def literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    return "'" + value.replace("'", "''") + "'"


def insert(table, columns, rows):
    values = ",\n".join("(" + ", ".join(map(literal, row)) + ")" for row in rows)
    return f"INSERT INTO {table} ({columns}) VALUES\n{values};\n" if rows else ""


def library_dataset(seed):
    reader_id = lambda n: seed * 100 + n
    isbn = lambda n: f"{seed:02d}{n:011d}"
    readers = [
        (1, "Иванов", "Иван", "Москва, ул. Книжная 1"),
        (2, f"Петров{seed}", "Пётр", "Москва, ул. Книжная 2"),
        (3, f"Сидоров{seed}", "Сидор", "Санкт-Петербург, пр. Невский 3"),
        (4, f"Петров{seed}", "Анна", "Москва, ул. Книжная 4"),
        (5, "Иванов", "Пётр", "Тверь, ул. Центральная 5"),
        (6, f"Петров{seed}", "Иван", "Москва"),
        (7, f"Орлова{seed}", "Мария", "Московская область, Химки"),
        (8, f"Никитин{seed}", "Никита", "Москва, ул. Книжная 8"),
    ]
    books = [(isbn(n), f"Издание {seed}-{n}", f"Автор {seed}-{(n + 1) // 2}",
              100 + n, 2000 + n, "Учебное издательство") for n in range(1, 9)]
    categories = [("Горы", None), ("Путешествия", None), ("Приключения", None),
                  ("Альпинизм", "Горы"), ("Походы", "Путешествия")]
    book_categories = [(1, "Горы"), (2, "Горы"), (2, "Путешествия"),
                       (3, "Горы"), (3, "Приключения"), (4, "Альпинизм"),
                       (5, "Горы"), (5, "Походы"), (6, "Приключения"),
                       (7, "Путешествия")]
    copies = [(isbn(n), 1, f"Полка {n}") for n in range(1, 9)]
    copies += [(isbn(1), 2, "Полка 9"), (isbn(2), 2, "Полка 10")]
    borrowings = [(1, 1, 1, "2024-01-15"), (1, 2, 1, None), (1, 2, 2, "2024-02-01"),
                  (1, 6, 1, None),
                  (2, 1, 2, "2024-03-01"), (3, 3, 1, None), (3, 4, 1, "2024-03-02"),
                  (4, 1, 1, None), (4, 2, 1, "2024-03-03"), (5, 2, 2, None), (5, 7, 1, None),
                  (6, 1, 2, "2099-01-01"), (6, 8, 1, None), (7, 5, 1, None), (7, 6, 1, None)]
    names = {n: (last, first) for n, last, first, _ in readers}
    expected = {
        "library_1": [("Иванов",), (f"Петров{seed}",), (f"Никитин{seed}",)],
        "library_2": [(books[n - 1][2], books[n - 1][1]) for n in (1, 2, 6)],
        "library_3": [(isbn(n),) for n in (1, 3, 5)],
        "library_4": [names[n] for n in (1, 2, 3, 4, 6)],
        "library_5": [names[n] for n in (2, 4, 5, 6, 7)],
    }
    sql = "TRUNCATE Borrowing, Copy, BookCategory, Book, Category, Publisher, Reader RESTART IDENTITY;\n"
    sql += insert("Reader", "ID, LastName, FirstName, Address, BirthDate",
                  [(reader_id(n), last, first, address, "1990-01-01")
                   for n, last, first, address in reversed(readers)])
    sql += insert("Publisher", "PubName, PubKind, Address",
                  [("Учебное издательство", "Independent", "Москва")])
    sql += insert("Book", "ISBN, Title, Author, Number_of_pages, Year, Publisher_Name", reversed(books))
    sql += insert("Category", "CategoryName, ParentCat", categories)
    sql += insert("Copy", "ISBN, CopyNumber, Position", copies)
    sql += insert("BookCategory", "ISBN, CategoryName", [(isbn(n), cat) for n, cat in book_categories])
    sql += insert("Borrowing", "ID, ISBN, CopyNumber, ReturnDate",
                  [(reader_id(r), isbn(b), copy, date) for r, b, copy, date in reversed(borrowings)])
    return Dataset(f"library-{seed}", sql, expected)


def train_dataset(seed):
    m1, m2, p1, p2, t1, t2, novgorod, kazan = [
        f"{name}-{seed}" for name in ("Ленинградский вокзал", "Октябрьская",
                                     "Московский вокзал", "Ладожский вокзал",
                                     "Центральная", "Южная", "Новгородская", "Казанская")
    ]
    cities = [("Москва", "Центральный"), ("Санкт-Петербург", "Северо-Западный"),
              ("Тверь", "Центральный"), ("Великий Новгород", "Северо-Западный"),
              ("Казань", "Приволжский"), ("Москва", "Другой регион")]
    stations = [(m1, 8, *cities[0]), (m2, 4, *cities[0]),
                (p1, 12, *cities[1]), (p2, 6, *cities[1]),
                (t1, 5, *cities[2]), (t2, 3, *cities[2]),
                (novgorod, 2, *cities[3]), (kazan, 7, *cities[4])]
    connections = []

    def leg(n, origin, target, day, departure, arrival, *, arrival_day=None):
        connections.append((origin, target, seed * 100 + n,
                            f"{day} {departure}:00", f"{arrival_day or day} {arrival}:00"))

    leg(1, m1, t1, "2024-03-01", "08:00", "10:00")
    leg(2, t1, p1, "2024-03-01", "10:00", "14:00")
    leg(3, m2, t1, "2024-03-01", "07:00", "09:00")
    leg(1, m1, t1, "2024-03-01", "12:00", "14:00")
    leg(4, m1, novgorod, "2024-03-02", "06:00", "08:00")
    leg(5, novgorod, p2, "2024-03-02", "09:00", "13:00")
    leg(6, novgorod, p2, "2024-03-02", "10:00", "15:00")
    leg(7, m1, t1, "2024-03-03", "06:00", "08:00")
    leg(7, t1, p1, "2024-03-03", "08:05", "11:00")
    leg(7, m1, p1, "2024-03-03", "06:00", "11:00")
    leg(8, m1, t1, "2024-03-04", "08:00", "12:00")
    leg(9, t1, p1, "2024-03-04", "11:00", "14:00")
    leg(10, m1, t1, "2024-03-05", "22:00", "23:00")
    leg(11, t1, p1, "2024-03-06", "00:30", "04:00")
    leg(12, m1, t1, "2024-03-07", "08:00", "10:00")
    leg(13, t2, p1, "2024-03-07", "11:00", "14:00")
    leg(14, kazan, t1, "2024-03-08", "08:00", "10:00")
    leg(15, t1, p1, "2024-03-08", "11:00", "14:00")
    leg(16, m1, t1, "2024-03-09", "08:00", "10:00")
    leg(17, t1, kazan, "2024-03-09", "11:00", "14:00")
    leg(18, m1, novgorod, "2024-01-10", "08:00", "10:00")
    leg(19, novgorod, p1, "2024-02-10", "11:00", "14:00")
    leg(20, m1, novgorod, "2024-03-11", "08:00", "10:00")
    leg(21, novgorod, p1, "2025-03-11", "11:00", "14:00")
    leg(22, t1, m1, "2024-03-12", "08:00", "10:00")
    leg(23, m1, p1, "2024-03-13", "08:00", "12:00")
    leg(24, m1, t1, "2024-03-14", "23:00", "01:00", arrival_day="2024-03-15")
    leg(25, t1, p1, "2024-03-15", "02:00", "04:00")
    trains = {}
    for origin, target, number, _, _ in connections:
        if number not in trains:
            trains[number] = (number, 8, origin, target)
    trains[seed * 100 + 7] = (seed * 100 + 7, 8, m1, p1)
    city_of = {name: city for name, _, city, _ in stations}
    direct = [(origin, target, str(number), departure, arrival)
              for origin, target, number, departure, arrival in connections
              if city_of[origin] == "Москва" and city_of[target] == "Тверь"]
    transfers = []
    for origin, transfer, first, departure, arrival in connections:
        for start, target, second, onward, final in connections:
            if (city_of[origin] == "Москва" and city_of[target] == "Санкт-Петербург"
                    and transfer == start and first != second and onward >= arrival
                    and departure[:10] == final[:10]):
                transfers.append((str(first), str(second), transfer, departure, final))
    sql = "TRUNCATE Connection, Train, Station, City;\n"
    sql += insert("City", "Name, Region", cities)
    sql += insert("Station", "Name, Tracks, CityName, Region", reversed(stations))
    sql += insert("Train", "TrainNr, Length, StartStationName, EndStationName", trains.values())
    sql += insert("Connection", "FromStation, ToStation, TrainNr, Departure, Arrival", reversed(connections))
    return Dataset(f"train-{seed}", sql, {"train_1": direct, "train_2": transfers})


def datasets(database):
    factory = library_dataset if database == "library" else train_dataset
    result = [factory(seed) for seed in (1, 7, 19)]
    truncate = result[0].sql.split("\n", 1)[0]
    result.append(Dataset(f"{database}-empty", truncate,
                          {key: [] for key in WIDTHS if key.startswith(database + "_")}))
    return result
