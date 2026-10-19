from __future__ import annotations

import unittest

from sql_fixtures import WIDTHS, datasets
from sql_helpers import ROOT, Postgres, assert_rows, read_answers


class SqlAnswersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.answers = read_answers((ROOT / "src" / "answers.md").read_text())
        cls.postgres = Postgres()
        cls.addClassCleanup(cls.postgres.stop)

    def check_answer(self, key):
        query = self.answers.get(key, "")
        self.assertTrue(query.strip(), f"{key}: заполните SQL-блок в src/answers.md.")
        if not self.postgres.started:
            self.postgres.start()
        database = key.split("_", 1)[0]
        for dataset in datasets(database):
            with self.subTest(dataset=dataset.name):
                self.postgres.psql(database, input=dataset.sql)
                rows = self.postgres.evaluate(database, query, WIDTHS[key])
                assert_rows(rows, dataset.expected[key])

    def test_library_1(self):
        self.check_answer("library_1")

    def test_library_2(self):
        self.check_answer("library_2")

    def test_library_3(self):
        self.check_answer("library_3")

    def test_library_4(self):
        self.check_answer("library_4")

    def test_library_5(self):
        self.check_answer("library_5")

    def test_train_1(self):
        self.check_answer("train_1")

    def test_train_2(self):
        self.check_answer("train_2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
