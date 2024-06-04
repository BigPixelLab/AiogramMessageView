import uuid
import typing as t
from datetime import datetime

from hulio.core.interfaces.database import IDatabaseProvider


TRow = list[t.Any]
TTable = tuple[dict[uuid.UUID, TRow], list[str]]
TSchema = dict[str, TTable]
TDatabase = dict[str, TSchema]


class MemoryStorageProvider(IDatabaseProvider):
    def __init__(self):
        self._database: TDatabase = {}

    def ensure_schema(self, schema_name: str):
        self._database.setdefault(schema_name, {})

    def ensure_table(self, schema_name: str, table_name: str, columns: dict[str, type]):
        self._database[schema_name].setdefault(
            table_name,
            ({}, ['created_at', *columns.keys()])
        )

    def insert(self, schema_name: str, table_name: str, record_id: uuid.UUID, values: dict[str, t.Any]):
        table, table_columns = self._database[schema_name][table_name]
        if set(table_columns) - {'created_at'} != set(values.keys()):
            raise ValueError('Invalid columns:', set(table_columns) - {'created_at'}, set(values.keys()))
        items = sorted(values.items(), key=lambda item: table_columns.index(item[0]))
        table[record_id] = [datetime.now(), *(item[1] for item in items)]

    def select(self, schema_name: str, table_name: str, columns: list[str] = None, where: dict[str, t.Any] = None, last_inserted: bool = False) -> list[TRow]:
        table, table_columns = self._database[schema_name][table_name]
        if columns is None:
            columns = table_columns
        if where is None:
            where = {}
        rows = list(filter(
            lambda row: all(
                row[table_columns.index(col)] == cond
                for col, cond in where.items()
            ),
            table.values()
        ))
        if not last_inserted:
            return [
                [
                    row[table_columns.index(col)]
                    for col in columns
                ]
                for row in rows
            ]
        # item[0] is 'created_at' field
        row = sorted(rows, key=lambda item: item[0])[-1]
        return [
            row[table_columns.index(col)]
            for col in columns
        ]

    def get(self, schema_name: str, table_name: str, columns: list[str], record_id: uuid.UUID) -> t.Optional[TRow]:
        table, table_columns = self._database[schema_name][table_name]
        try:
            row = table[record_id]
        except KeyError:
            return None
        return [
            row[table_columns.index(col)]
            for col in columns
        ]

    def exists(self, schema_name: str, table_name: str, where: dict[str, t.Any]) -> bool:
        return len(self.select(schema_name, table_name, [], where)) != 0

    def update(self, schema_name: str, table_name: str, values: dict[str, t.Any], record_id: uuid.UUID):
        table, table_columns = self._database[schema_name][table_name]
        for col, val in values.items():
            table[record_id][table_columns.index(col)] = val

    def delete(self, schema_name: str, table_name: str, record_id: uuid.UUID):
        table, _ = self._database[schema_name][table_name]
        del table[record_id]
