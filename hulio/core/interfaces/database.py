import typing as t
import uuid
from abc import ABC, abstractmethod

from pydantic import BaseModel


class ComponentRecord(BaseModel):
    record_id: uuid.UUID
    parent_record_id: t.Optional[uuid.UUID]
    message_record_id: uuid.UUID
    component_id: str
    state_json: str
    is_enabled: bool


class MessageRecord(BaseModel):
    record_id: uuid.UUID
    bot_id: int
    chat_id: int
    user_id: int
    message_id: int

    media_id: str
    media_type: t.Literal[
        'nm',  # No media
        'lp',  # LinkPreview
        'p',  # Photo
        'a',  # Animation
        'v',  # Video
        'd',  # Document
        'au'  # Audio
    ]


class IDatabaseController(t.Protocol):
    def setup(self):
        raise NotImplementedError

    def component_track(self, record: ComponentRecord):
        raise NotImplementedError

    def component_untrack(self, record_id: uuid.UUID):
        raise NotImplementedError

    def component_update(self, record: ComponentRecord):
        raise NotImplementedError

    def component_get_focused(self, bot_id: int, chat_id: int, user_id: int) -> ComponentRecord:
        raise NotImplementedError

    def component_get(self, record_id: uuid.UUID) -> ComponentRecord:
        raise NotImplementedError

    def message_track(self, record: MessageRecord):
        raise NotImplementedError

    def message_untrack(self, record_id: uuid.UUID):
        raise NotImplementedError

    def message_get(self, record_id: uuid.UUID) -> MessageRecord:
        raise NotImplementedError


class IDatabaseProvider(t.Protocol):
    def ensure_schema(self, schema_name: str):
        raise NotImplementedError

    def ensure_table(self, schema_name: str, table_name: str, columns: dict[str, type]):
        raise NotImplementedError

    def insert(self, schema_name: str, table_name: str, record_id: uuid.UUID, values: dict[str, t.Any]):
        raise NotImplementedError

    def select(self, schema_name: str, table_name: str, columns: list[str] = None, where: dict[str, t.Any] = None, last_inserted: bool = False) -> list[list[t.Any]]:
        raise NotImplementedError

    def get(self, schema_name: str, table_name: str, record_id: uuid.UUID, columns: list[str] = None) -> t.Optional[list[t.Any]]:
        raise NotImplementedError

    def exists(self, schema_name: str, table_name: str, where: dict[str, t.Any]) -> bool:
        raise NotImplementedError

    def update(self, schema_name: str, table_name: str, values: dict[str, t.Any], record_id: uuid.UUID):
        raise NotImplementedError

    def delete(self, schema_name: str, table_name: str, record_id: uuid.UUID):
        raise NotImplementedError
