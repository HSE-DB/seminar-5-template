from __future__ import annotations

import unittest
from unittest.mock import Mock

from sql_fixtures import WIDTHS, datasets, literal
from sql_helpers import Postgres, assert_rows, query_body, read_answers, read_result


class MarkdownTests(unittest.TestCase):
    def test_repeated_question_numbers_belong_to_their_parts(self):
        answers = read_answers("""# Ответы
## Часть 1: Библиотечная система
### Вопрос 1.
```sql
SELECT '### Вопрос 2' AS title;
```
### Вопрос 2
~~~SQL
SELECT 2;
~~~
## Часть 2: Поезда
### Вопрос 1
```sql
SELECT 3;
```
""")
        self.assertEqual(answers, {"library_1": "SELECT '### Вопрос 2' AS title;",
                                   "library_2": "SELECT 2;", "train_1": "SELECT 3;"})

    def test_empty_answer_is_preserved(self):
        self.assertEqual(read_answers("## Часть 1: Библиотека\n### Вопрос 1\n```sql\n\n```"),
                         {"library_1": ""})

    def test_duplicate_sql_blocks_are_rejected(self):
        with self.assertRaisesRegex(AssertionError, "один SQL-блок"):
            read_answers("## Часть 1: Библиотека\n### Вопрос 1\n```sql\nSELECT 1;\n```\n"
                         "```sql\nSELECT 2;\n```")

    def test_unclosed_sql_block_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "Закройте"):
            read_answers("## Часть 1: Библиотека\n### Вопрос 1\n```sql\nSELECT 1;")

    def test_sql_without_question_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "заголовками"):
            read_answers("## Часть 1: Библиотека\n```sql\nSELECT 1;\n```")

    def test_non_sql_fences_do_not_create_questions(self):
        self.assertEqual(read_answers("```markdown\n## Часть 1: Библиотека\n### Вопрос 1\n```"), {})


class ResultTests(unittest.TestCase):
    def test_row_order_and_column_aliases_do_not_matter(self):
        rows = read_result('surname,name\nПетров,Пётр\nИванов,Иван\n', 2)
        assert_rows(rows, [("Иванов", "Иван"), ("Петров", "Пётр")])

    def test_csv_handles_commas_quotes_and_newlines(self):
        rows = read_result('author,title\n"Автор, первый","Название ""книги""\nв две строки"\n', 2)
        self.assertEqual(rows, [("Автор, первый", 'Название "книги"\nв две строки')])

    def test_duplicate_rows_are_rejected(self):
        with self.assertRaisesRegex(AssertionError, "Лишние строки"):
            assert_rows([("Иванов",), ("Иванов",)], [("Иванов",)])

    def test_missing_rows_are_rejected(self):
        with self.assertRaisesRegex(AssertionError, "Недостающие строки"):
            assert_rows([], [("Иванов",)])

    def test_wrong_column_order_is_rejected(self):
        with self.assertRaises(AssertionError):
            assert_rows([("Иван", "Иванов")], [("Иванов", "Иван")])

    def test_wrong_projection_is_rejected_even_when_empty(self):
        with self.assertRaisesRegex(AssertionError, "2 столбцов"):
            read_result("lastname\n", 2)

    def test_empty_result_keeps_its_column_count(self):
        self.assertEqual(read_result("lastname,firstname\n", 2), [])


class ExecutionTests(unittest.TestCase):
    def test_final_semicolon_is_optional(self):
        self.assertEqual(query_body(" SELECT 1; \n"), "SELECT 1")
        self.assertEqual(query_body("SELECT 1"), "SELECT 1")

    def test_empty_query_is_rejected(self):
        for text in ("", " \n", ";", "-- SELECT 1", "/* SELECT 1 */"):
            with self.subTest(text=text), self.assertRaises(AssertionError):
                query_body(text)

    def test_trailing_comments_after_semicolon_are_allowed(self):
        self.assertEqual(query_body("SELECT 1; -- ответ\n/* готово */"), "SELECT 1")
        self.assertEqual(query_body("SELECT 1; /* outer /* inner */ end */"), "SELECT 1")

    def test_comment_markers_inside_strings_are_preserved(self):
        for query in ("SELECT 'текст; -- не комментарий'", 'SELECT 1 AS "name; --"',
                      "SELECT $$a; -- b$$", "SELECT $tag$a; /* b */$tag$",
                      "SELECT E'it\\'s; -- text'", "SELECT 'a''; -- b'"):
            with self.subTest(query=query):
                self.assertEqual(query_body(query + "; -- конец"), query)

    def test_multiple_statements_are_not_joined(self):
        self.assertEqual(query_body("SELECT 1; SELECT 2;"), "SELECT 1; SELECT 2")

    def test_unclosed_block_comment_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "Закройте комментарий"):
            query_body("SELECT 1; /* comment")

    def test_query_runs_read_only_with_timeout_as_separate_argument(self):
        postgres = Postgres()
        postgres.command = Mock(return_value=Mock(stdout="value\n1\n"))
        self.assertEqual(postgres.evaluate("library", "SELECT 1;", 1), [("1",)])
        args = postgres.command.call_args.args[0]
        sql = args[-1]
        self.assertEqual(args[-2], "-c")
        self.assertIn("grader", args)
        self.assertIn("-X", args)
        self.assertIn("ON_ERROR_STOP=1", args)
        self.assertTrue(sql.startswith("BEGIN READ ONLY;"))
        self.assertIn("statement_timeout = '3s'", sql)
        self.assertIn("COPY (\nSELECT 1\n)", sql)
        self.assertTrue(sql.endswith("ROLLBACK;"))


class DatasetTests(unittest.TestCase):
    def test_datasets_cover_all_tasks_and_empty_results(self):
        for database, count in (("library", 5), ("train", 2)):
            cases = datasets(database)
            self.assertEqual(len(cases), 4)
            for dataset in cases:
                self.assertEqual(len(dataset.expected), count)
                self.assertTrue(dataset.sql.startswith("TRUNCATE "))
                for key, rows in dataset.expected.items():
                    self.assertTrue(key.startswith(database + "_"))
                    self.assertTrue(all(len(row) == WIDTHS[key] for row in rows))
                    self.assertEqual(len(rows), len(set(rows)))
            self.assertTrue(all(not rows for rows in cases[-1].expected.values()))

    def test_changed_ids_and_values_defeat_constant_answers(self):
        for database in ("library", "train"):
            first, second, *_ = datasets(database)
            for key in first.expected:
                self.assertNotEqual(first.expected[key], second.expected[key])

    def test_train_cases_include_four_valid_transfers(self):
        for dataset in datasets("train")[:-1]:
            self.assertEqual(len(dataset.expected["train_2"]), 4)

    def test_sql_literals_escape_apostrophes(self):
        self.assertEqual(literal("O'Brien"), "'O''Brien'")
        self.assertEqual(literal(None), "NULL")
        self.assertEqual(literal(123), "123")


if __name__ == "__main__":
    unittest.main(verbosity=2)
