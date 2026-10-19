from __future__ import annotations

import csv
import io
import re
import subprocess
import time
import uuid
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTION = re.compile(r"###\s+Вопрос\s+([1-5])\.?\s*")
PART = re.compile(r"##\s+Часть\s+([12])\s*:[^\n]*")


def read_answers(text):
    answers = {}
    part = question = fence = None
    sql_block = False
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if fence:
            if re.fullmatch(re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*", stripped):
                if sql_block:
                    key = f"{'library' if part == 1 else 'train'}_{question}"
                    if key in answers:
                        raise AssertionError(f"{key}: оставьте один SQL-блок для вопроса.")
                    answers[key] = "\n".join(lines).strip()
                fence = None
            else:
                lines.append(line)
            continue
        if match := PART.fullmatch(stripped):
            part, question = int(match[1]), None
        elif match := QUESTION.fullmatch(stripped):
            question = int(match[1])
        elif match := re.fullmatch(r"(`{3,}|~{3,})([^`~]*)", stripped):
            sql_block = match[2].strip().lower() == "sql"
            if sql_block and (part is None or question is None):
                raise AssertionError("SQL-блок должен находиться под заголовками части и вопроса.")
            fence, lines = match[1], []
    if fence and sql_block:
        raise AssertionError("Закройте SQL-блок в src/answers.md.")
    return answers


def query_body(query):
    query = query.strip()
    position = end = 0
    while position < len(query):
        if query[position].isspace():
            position += 1
            continue
        if query.startswith("--", position):
            newline = query.find("\n", position)
            position = len(query) if newline == -1 else newline + 1
            continue
        if query.startswith("/*", position):
            depth = 1
            position += 2
            while position < len(query) and depth:
                if query.startswith("/*", position):
                    depth += 1
                    position += 2
                elif query.startswith("*/", position):
                    depth -= 1
                    position += 2
                else:
                    position += 1
            if depth:
                raise AssertionError("Закройте комментарий /* ... */ в запросе.")
            continue
        if query[position] in "'\"":
            quote = query[position]
            escaped = (quote == "'" and position > 0 and query[position - 1] in "eE"
                       and (position == 1 or not query[position - 2].isalnum()))
            position += 1
            while position < len(query):
                if escaped and query[position] == "\\":
                    position += 2
                elif query[position] == quote:
                    position += 1
                    if position < len(query) and query[position] == quote:
                        position += 1
                    else:
                        break
                else:
                    position += 1
        elif match := re.match(r"\$(?:[a-zA-Z_][a-zA-Z_0-9]*)?\$", query[position:]):
            closing = query.find(match[0], position + len(match[0]))
            position = len(query) if closing == -1 else closing + len(match[0])
        else:
            position += 1
        end = position
    query = query[:end].rstrip()
    if query.endswith(";"):
        query = query[:-1].rstrip()
    if not query:
        raise AssertionError("Заполните SQL-блок запроса в src/answers.md.")
    return query


def read_result(output, width):
    rows = list(csv.reader(io.StringIO(output)))
    if not rows or len(rows[0]) != width:
        found = len(rows[0]) if rows else 0
        raise AssertionError(f"Ожидается {width} столбцов в указанном в задании порядке, получено {found}.")
    return [tuple(row) for row in rows[1:]]


def assert_rows(actual, expected):
    actual, expected = Counter(actual), Counter(expected)
    if actual != expected:
        missing = list((expected - actual).elements())[:5]
        extra = list((actual - expected).elements())[:5]
        raise AssertionError(f"Результат запроса не совпадает.\nНедостающие строки: {missing!r}"
                             f"\nЛишние строки (включая повторы): {extra!r}")


class Postgres:
    def __init__(self):
        self.name = "hse5-check-" + uuid.uuid4().hex[:12]
        self.started = False

    def command(self, args, *, input=None, timeout=30, check=True):
        try:
            result = subprocess.run(args, input=input, text=True, capture_output=True, timeout=timeout)
        except FileNotFoundError as error:
            raise AssertionError("Установите и запустите Docker для проверки SQL.") from error
        except subprocess.TimeoutExpired as error:
            raise AssertionError(f"Команда не завершилась за {timeout} секунд: {' '.join(args[:5])}") from error
        if check and result.returncode:
            raise AssertionError((result.stderr or result.stdout).strip()[-3000:])
        return result

    def psql(self, database, *, query=None, input=None, user="postgres"):
        args = ["docker", "exec", "-i", self.name, "psql", "-X", "-q",
                "-v", "ON_ERROR_STOP=1", "-U", user, "-d", database]
        if query is not None:
            args += ["-c", query]
        return self.command(args, input=input).stdout

    def start(self):
        self.command(["docker", "run", "-d", "--name", self.name,
                      "--label", "hse.seminar=5-autograding",
                      "-e", "POSTGRES_HOST_AUTH_METHOD=trust", "postgres:18"], timeout=180)
        self.started = True
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            ready = self.command(["docker", "exec", self.name, "pg_isready", "-h", "127.0.0.1",
                                  "-U", "postgres"], check=False)
            if ready.returncode == 0:
                break
            time.sleep(0.25)
        else:
            logs = self.command(["docker", "logs", self.name], check=False)
            raise AssertionError("PostgreSQL не запустился:\n" + logs.stderr[-3000:])
        self.psql("postgres", query="CREATE ROLE grader LOGIN;")
        for database in ("library", "train"):
            self.psql("postgres", query=f"CREATE DATABASE {database};")
            self.psql(database, input=(ROOT / "docker" / "sql" / database / "init.sql").read_text())
            self.psql(database, query="GRANT USAGE ON SCHEMA public TO grader; "
                                     "GRANT SELECT ON ALL TABLES IN SCHEMA public TO grader;")

    def stop(self):
        if self.started:
            self.command(["docker", "rm", "-f", "-v", self.name])
            self.started = False

    def evaluate(self, database, query, width):
        body = query_body(query)
        sql = ("BEGIN READ ONLY; SET LOCAL statement_timeout = '3s'; "
               "SET LOCAL lock_timeout = '1s'; SET LOCAL DateStyle = 'ISO, YMD';\n"
               f"COPY (\n{body}\n) TO STDOUT WITH (FORMAT csv, HEADER true, NULL '\\N');\n"
               "ROLLBACK;")
        return read_result(self.psql(database, query=sql, user="grader"), width)
