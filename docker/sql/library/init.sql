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

INSERT INTO Reader (ID, LastName, FirstName, Address, BirthDate) VALUES
(10000, 'Иванов', 'Иван', 'Москва, ул. Пушкина 10', '1990-05-15'),
(20000, 'Петров', 'Пётр', 'Москва, ул. Ленина 20', '1985-03-22'),
(30000, 'Сидоров', 'Сидор', 'Санкт-Петербург, пр. Невский 30', '1988-07-10'),
(40000, 'Смирнова', 'Анна', 'Москва, ул. Тверская 40', '1992-11-25'),
(50000, 'Кузнецов', 'Алексей', 'Екатеринбург, ул. Мира 50', '1987-09-18');

INSERT INTO Category (CategoryName, ParentCat) VALUES
('Путешествия', NULL), ('Горы', NULL), ('Приключения', NULL),
('Альпинизм', 'Горы'), ('Треккинг', 'Путешествия');

INSERT INTO Publisher (PubName, PubKind, Address) VALUES
('Эксмо', 'Commercial', 'Москва, ул. Издательская 1'),
('АСТ', 'Commercial', 'Москва, ул. Книжная 2'),
('Альпина', 'Independent', 'Москва, ул. Горная 3');

INSERT INTO Book (ISBN, Title, Author, Number_of_pages, Year, Publisher_Name) VALUES
('1234567890123', 'Горы Кавказа', 'Пётр Семенов', 300, 2020, 'Эксмо'),
('2345678901234', 'Путешествие в Альпы', 'Иван Горный', 250, 2019, 'АСТ'),
('3456789012345', 'Восхождение на Эверест', 'Джон Смит', 400, 2021, 'Альпина'),
('4567890123456', 'Треккинг в Непале', 'Майк Хилл', 350, 2018, 'Эксмо'),
('5678901234567', 'Затерянный мир', 'Артур Конан Дойл', 280, 1912, 'АСТ'),
('6789012345678', 'Основы альпинизма', 'Иван Горный', 180, 2022, 'АСТ');

INSERT INTO BookCategory (ISBN, CategoryName) VALUES
('1234567890123', 'Горы'),
('2345678901234', 'Путешествия'), ('2345678901234', 'Горы'),
('3456789012345', 'Горы'), ('3456789012345', 'Треккинг'),
('4567890123456', 'Путешествия'),
('5678901234567', 'Приключения'), ('6789012345678', 'Альпинизм');

INSERT INTO Copy (ISBN, CopyNumber, Position) VALUES
('1234567890123', 1, 'Полка А1'), ('1234567890123', 2, 'Полка А2'),
('2345678901234', 1, 'Полка Б1'), ('2345678901234', 2, 'Полка Б2'),
('3456789012345', 1, 'Полка В1'), ('4567890123456', 1, 'Полка Г1'),
('5678901234567', 1, 'Полка Д1'), ('6789012345678', 1, 'Полка Е1');

INSERT INTO Borrowing (ID, ISBN, CopyNumber, ReturnDate) VALUES
(10000, '1234567890123', 1, '2024-01-15'),
(10000, '2345678901234', 1, '2024-02-01'),
(10000, '2345678901234', 2, NULL),
(20000, '1234567890123', 2, NULL),
(30000, '3456789012345', 1, '2024-03-01'),
(40000, '1234567890123', 1, '2024-03-15'),
(40000, '2345678901234', 1, NULL),
(50000, '4567890123456', 1, '2024-03-20');

SELECT setval(pg_get_serial_sequence('reader', 'id'), (SELECT MAX(ID) FROM Reader));
