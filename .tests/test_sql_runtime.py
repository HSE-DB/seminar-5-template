from __future__ import annotations

import unittest

from sql_helpers import Postgres


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.postgres = Postgres()
        cls.addClassCleanup(cls.postgres.stop)
        cls.postgres.start()

    def test_provided_library_seed_has_ivans_borrowings(self):
        rows = self.postgres.evaluate("library", """
            SELECT COUNT(*) FROM Borrowing b JOIN Reader r ON r.ID = b.ID
            WHERE r.LastName = 'Иванов' AND r.FirstName = 'Иван'
        """, 1)
        self.assertEqual(rows, [("3",)])

    def test_both_database_schemas_are_loaded(self):
        self.assertEqual(self.postgres.evaluate("train", "SELECT COUNT(*) FROM City", 1), [("9",)])

    def test_cte_comments_and_optional_semicolon(self):
        rows = self.postgres.evaluate("library", """
            -- Синтаксис PostgreSQL и комментарии допустимы.
            WITH sample AS (SELECT 'Москва' AS city)
            SELECT city FROM sample; -- конец запроса
        """, 1)
        self.assertEqual(rows, [("Москва",)])

    def test_csv_preserves_unicode_quotes_and_newlines(self):
        self.assertEqual(self.postgres.evaluate("library", """SELECT E'Книга, "А"\nтом 2'""", 1),
                         [('Книга, "А"\nтом 2',)])

    def test_multiple_statements_fail_without_breaking_next_query(self):
        with self.assertRaises(AssertionError):
            self.postgres.evaluate("library", "SELECT 1; SELECT 2;", 1)
        self.assertEqual(self.postgres.evaluate("library", "SELECT 1", 1), [("1",)])

    def test_data_modifying_cte_is_rejected(self):
        before = self.postgres.evaluate("library", "SELECT COUNT(*) FROM Reader", 1)
        with self.assertRaises(AssertionError):
            self.postgres.evaluate("library", """
                WITH deleted AS (DELETE FROM Reader RETURNING ID) SELECT ID FROM deleted
            """, 1)
        self.assertEqual(self.postgres.evaluate("library", "SELECT COUNT(*) FROM Reader", 1), before)

    def test_long_query_times_out(self):
        with self.assertRaisesRegex(AssertionError, "statement timeout"):
            self.postgres.evaluate("library", "SELECT pg_sleep(4)", 1)

    def test_empty_result_with_wrong_projection_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "2 столбцов"):
            self.postgres.evaluate("library", "SELECT LastName FROM Reader WHERE false", 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
