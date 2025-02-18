-- Создаем таблицы
CREATE TABLE IF NOT EXISTS Reader (
    ID SERIAL PRIMARY KEY,
    LastName VARCHAR(50) NOT NULL,
    FirstName VARCHAR(50) NOT NULL,
    Address VARCHAR(200) NOT NULL,
    BirthDate DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS Publisher (
    PubName VARCHAR(100) PRIMARY KEY,
    PubKind VARCHAR(50),
    Address VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS Book (
    ISBN VARCHAR(13) PRIMARY KEY,
    Title VARCHAR(200) NOT NULL,
    Author VARCHAR(100) NOT NULL,
    Number_of_pages INT NOT NULL,
    Year INT NOT NULL,
    Publisher_Name VARCHAR(100),
    FOREIGN KEY (Publisher_Name) REFERENCES Publisher(PubName) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS Category (
    CategoryName VARCHAR(50) PRIMARY KEY,
    ParentCat VARCHAR(50),
    FOREIGN KEY (ParentCat) REFERENCES Category(CategoryName) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Copy (
    ISBN VARCHAR(13),
    CopyNumber INT,
    Position VARCHAR(50),
    PRIMARY KEY (ISBN, CopyNumber),
    FOREIGN KEY (ISBN) REFERENCES Book(ISBN) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS BookCategory (
    ISBN VARCHAR(13),
    CategoryName VARCHAR(50),
    PRIMARY KEY (ISBN, CategoryName),
    FOREIGN KEY (ISBN) REFERENCES Book(ISBN) ON DELETE CASCADE,
    FOREIGN KEY (CategoryName) REFERENCES Category(CategoryName) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Borrowing (
    ID INT,
    ISBN VARCHAR(13),
    CopyNumber INT,
    ReturnDate DATE,
    PRIMARY KEY (ID, ISBN, CopyNumber),
    FOREIGN KEY (ID) REFERENCES Reader(ID),
    FOREIGN KEY (ISBN, CopyNumber) REFERENCES Copy(ISBN, CopyNumber) ON DELETE CASCADE
);

-- Процедура генерации категорий
DO
$$
    DECLARE
        i INT := 1;
    BEGIN
        -- Генерируем главные категории
        WHILE i <= 20
            LOOP
                INSERT INTO Category (CategoryName, ParentCat)
                VALUES (CONCAT('MainCategory', i), NULL);
                i := i + 1;
            END LOOP;

        -- Генерируем подкатегории
        i := 1;
        WHILE i <= 80
            LOOP
                INSERT INTO Category (CategoryName, ParentCat)
                VALUES (CONCAT('SubCategory', i),
                        (SELECT CategoryName FROM Category WHERE ParentCat IS NULL ORDER BY RANDOM() LIMIT 1));
                i := i + 1;
            END LOOP;
    END
$$ LANGUAGE plpgsql;

-- Процедура генерации издателей
DO
$$
    DECLARE
        i INT := 1;
    BEGIN
        WHILE i <= 1000
            LOOP
                INSERT INTO Publisher (PubName, PubKind, Address)
                VALUES (CONCAT('Publisher', i),
                        CASE
                            WHEN RANDOM() < 0.33 THEN 'Academic'
                            WHEN RANDOM() < 0.66 THEN 'Commercial'
                            ELSE 'Independent'
                            END,
                        CONCAT('Address ', i));
                i := i + 1;
            END LOOP;
    END
$$ LANGUAGE plpgsql;

-- Процедура генерации книг
DO $$
DECLARE
    i INT := 1;
BEGIN
    WHILE i <= 5000 LOOP
        -- Вставляем книгу
        INSERT INTO Book (ISBN, Title, Author, Number_of_pages, Year, Publisher_Name)
        VALUES (
            CONCAT('ISBN', LPAD(i::TEXT, 9, '0')),  -- ISBN сокращено до 13 символов
            CONCAT('Book Title ', i),
            CONCAT('Author ', i),
            FLOOR(100 + RANDOM() * 900),
            FLOOR(1900 + RANDOM() * 124),
            (SELECT PubName FROM Publisher ORDER BY RANDOM() LIMIT 1)
        );

        -- Присваиваем категории
        INSERT INTO BookCategory (ISBN, CategoryName)
        SELECT
            CONCAT('ISBN', LPAD(i::TEXT, 9, '0')),
            CategoryName
        FROM Category
        ORDER BY RANDOM()
        LIMIT 1 + FLOOR(RANDOM() * 5);

        i := i + 1;
    END LOOP;
END $$ LANGUAGE plpgsql;


-- Процедура генерации экземпляров книг
DO
$$
    DECLARE
        i INT := 1;
        new_isbn VARCHAR(13);
        new_copynumber INT;
    BEGIN
        WHILE i <= 20000
        LOOP
            -- Генерируем случайный ISBN и CopyNumber
            SELECT ISBN INTO new_isbn
            FROM Book
            ORDER BY RANDOM()
            LIMIT 1;

            new_copynumber := FLOOR(1 + RANDOM() * 10);

            -- Проверяем, существует ли уже такой ISBN с этим CopyNumber
            IF NOT EXISTS (
                SELECT 1
                FROM Copy
                WHERE ISBN = new_isbn AND CopyNumber = new_copynumber
            ) THEN
                -- Если нет, вставляем запись
                INSERT INTO Copy (ISBN, CopyNumber, Position)
                VALUES (
                    new_isbn,
                    new_copynumber,
                    CONCAT('Shelf-', FLOOR(1 + RANDOM() * 100))
                );
                i := i + 1;
            END IF;
        END LOOP;
    END
$$ LANGUAGE plpgsql;

-- Процедура генерации читателей
DO
$$
    DECLARE
        i INT := 1;
    BEGIN
        WHILE i <= 5000
            LOOP
                INSERT INTO Reader (LastName, FirstName, Address, BirthDate)
                VALUES (
                    CONCAT('LastName', i),
                    CONCAT('FirstName', i),
                    CONCAT('Address ', i),
                    CURRENT_DATE - INTERVAL '18 years' - INTERVAL '1 year' * FLOOR(RANDOM() * 52)
                );
                i := i + 1;
            END LOOP;
    END
$$ LANGUAGE plpgsql;

-- Процедура генерации заимствований книг
DO
$$
    DECLARE
        i INT := 1;
        reader_count INT;
        copy_count INT;
    BEGIN
        -- Получаем количество записей в таблицах Reader и Copy
        SELECT COUNT(*) INTO reader_count FROM Reader;
        SELECT COUNT(*) INTO copy_count FROM Copy;

        WHILE i <= 100
        LOOP
            -- Генерируем случайные индексы для выборки
            INSERT INTO Borrowing (ID, ISBN, CopyNumber, ReturnDate)
            SELECT r.ID,
                   c.ISBN,
                   c.CopyNumber,
                   CURRENT_DATE + INTERVAL '1 day' * FLOOR(RANDOM() * 30)
            FROM Reader r
            JOIN Copy c ON TRUE
            WHERE r.ID = (SELECT ID FROM Reader OFFSET FLOOR(RANDOM() * reader_count) LIMIT 1)
              AND c.ISBN = (SELECT ISBN FROM Copy OFFSET FLOOR(RANDOM() * copy_count) LIMIT 1)
            LIMIT 1;
            i := i + 1;
        END LOOP;
    END
$$ LANGUAGE plpgsql;


-- Тестовые данные для читателей, категорий, издателей, книг, категорий книг, экземпляров и заимствований
INSERT INTO Reader (ID, LastName, FirstName, Address, BirthDate)
VALUES (10000, 'Иванов', 'Иван', 'Москва, ул. Пушкина 10', '1990-05-15'),
       (20000, 'Петров', 'Петр', 'Москва, ул. Ленина 20', '1985-03-22'),
       (30000, 'Сидоров', 'Сидор', 'Санкт-Петербург, пр. Невский 30', '1988-07-10'),
       (40000, 'Смирнова', 'Анна', 'Москва, ул. Тверская 40', '1992-11-25'),
       (50000, 'Кузнецов', 'Алексей', 'Екатеринбург, ул. Мира 50', '1987-09-18');

INSERT INTO Category (CategoryName, ParentCat)
VALUES ('Путешествия', NULL),
       ('Горы', NULL),
       ('Приключения', NULL),
       ('Альпинизм', 'Горы'),
       ('Треккинг', 'Горы');

INSERT INTO Publisher (PubName, PubKind, Address)
VALUES ('Эксмо', 'Commercial', 'Москва, ул. Издательская 1'),
       ('АСТ', 'Commercial', 'Москва, ул. Книжная 2'),
       ('Альпина', 'Independent', 'Москва, ул. Горная 3');

INSERT INTO Book (ISBN, Title, Author, Number_of_pages, Year, Publisher_Name)
VALUES ('1234567890123', 'Горы Кавказа', 'Петр Семенов', 300, 2020, 'Эксмо'),
       ('2345678901234', 'Путешествие в Альпы', 'Иван Горный', 250, 2019, 'АСТ'),
       ('3456789012345', 'Восхождение на Эверест', 'Джон Смит', 400, 2021, 'Альпина'),
       ('4567890123456', 'Треккинг в Непале', 'Майк Хилл', 350, 2018, 'Эксмо'),
       ('5678901234567', 'Затерянный мир', 'Артур Конан Дойл', 280, 1912, 'АСТ');

INSERT INTO BookCategory (ISBN, CategoryName)
VALUES ('1234567890123', 'Горы'),
       ('2345678901234', 'Путешествия'),
       ('2345678901234', 'Горы'),
       ('3456789012345', 'Горы'),
       ('4567890123456', 'Путешествия'),
       ('5678901234567', 'Приключения');

INSERT INTO Copy (ISBN, CopyNumber, Position)
VALUES ('1234567890123', 1, 'Полка А1'),
       ('1234567890123', 2, 'Полка А2'),
       ('2345678901234', 1, 'Полка Б1'),
       ('3456789012345', 1, 'Полка В1'),
       ('4567890123456', 1, 'Полка Г1'),
       ('5678901234567', 1, 'Полка Д1');

-- Ensure the reader table has the necessary IDs
INSERT INTO Reader (ID, LastName, FirstName, Address, BirthDate)
VALUES (10001, 'Reader One', 'FirstName1', 'Address 1', '1990-01-01'),
       (10002, 'Reader Two', 'FirstName2', 'Address 2', '1991-02-02'),
       (10003, 'Reader Three', 'FirstName3', 'Address 3', '1992-03-03'),
       (10004, 'Reader Four', 'FirstName4', 'Address 4', '1993-04-04'),
       (10005, 'Reader Five', 'FirstName5', 'Address 5', '1994-05-05');

-- Insert into Borrowing table
INSERT INTO Borrowing (ID, ISBN, CopyNumber, ReturnDate)
VALUES (10001, '1234567890123', 1, '2024-01-15'),
       (10001, '2345678901234', 1, '2024-02-01'),
       (10002, '1234567890123', 2, NULL),
       (10003, '3456789012345', 1, '2024-03-01'),
       (10004, '1234567890123', 1, '2024-03-15'),
       (10005, '4567890123456', 1, '2024-03-20');