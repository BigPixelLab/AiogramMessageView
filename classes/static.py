import datetime
import uuid
from typing import TYPE_CHECKING, Protocol

from aiogram import Router
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, Message
from pydantic import BaseModel

if TYPE_CHECKING:
    from message_view import MessageView


__all__ = ('message_view_router',)


class ITemplate(Protocol):
    def __init__(self, path: str):
        """ Template is initialized from path to the file """

    def render(self, context: dict) -> dict:
        """ Renders template into arguments for bot.send_message and bot.edit_message """


class DatabaseFetchModel(BaseModel):
    view_id: str
    data: str
    created_at: datetime.datetime
    last_updated_at: datetime.datetime


class IDatabase(Protocol):
    def insert_view_record(self, record_id: uuid.UUID, view_id: str, data: str, created_at: datetime.datetime = None) -> None:
        """ Inserts new record into database """

    def update_view_record(self, record_id: uuid.UUID, data: str, last_updated_at: datetime.datetime = None) -> None:
        """ Updates existing record in database """

    def delete_view_record(self, record_id: uuid) -> None:
        """ Deletes existing record from database """

    def get_view_record(self, record_id: uuid.UUID) -> DatabaseFetchModel:
        """ Gets record from database """


class MemoryDatabase(IDatabase):
    def __init__(self):
        self.__database = {}

    def insert_view_record(self, record_id: uuid.UUID, view_id: str, data: str, created_at: datetime.datetime = None) -> None:
        self.__database[record_id] = DatabaseFetchModel(
            view_id=view_id,
            data=data,
            created_at=created_at or datetime.datetime.now(),
            last_updated_at=datetime.datetime.now()
        )

    def update_view_record(self, record_id: uuid.UUID, data: str, last_updated_at: datetime.datetime = None) -> None:
        val = self.__database[record_id]
        val.data = data
        val.last_updated_at = last_updated_at or datetime.datetime.now()

    def delete_view_record(self, record_id: uuid) -> None:
        del self.__database[record_id]

    def get_view_record(self, record_id: uuid.UUID) -> DatabaseFetchModel:
        return self.__database[record_id]


database: IDatabase = MemoryDatabase()

message_view_router = Router()


class TelegramMessageViewCallbackData(CallbackData, prefix='v'):
    record_id: uuid.UUID
    """ID of DB record, that stores message and chat data as well 
    as information about message-handling object"""
    action_id: str
    action_args: str


async def __handle_callback_query__(query: CallbackQuery, callback_data: TelegramMessageViewCallbackData):
    view = MessageView.from_record_id(callback_data.record_id)
    await view.simulate_button_press(query, callback_data.action_id, callback_data.action_args)


message_view_router.callback_query.register(
    TelegramMessageViewCallbackData.filter(),
    __handle_callback_query__
)


# async def __handle_message__(message: Message):
#     record_id = database.get_last_focused(message.chat.id)
#     view = MessageView.from_record_id(record_id)
#     await view.simulate_text_input(message)
#
#
# message_view_router.message.register(
#
# )
