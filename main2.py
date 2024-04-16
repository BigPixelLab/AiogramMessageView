import uuid
from asyncio import Lock
from typing import Optional, ClassVar, Callable, Hashable

from aiogram import Bot, Dispatcher
from aiogram.dispatcher.event.handler import CallableObject
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pydantic import BaseModel, Field, ConfigDict

TOKEN = '6786053401:AAGO9mhXYedvc_JVmVuTedDOkPm5dMfIoCI'


bot = Bot(token=TOKEN)
dp = Dispatcher()


class KeyLock:
    _locks: dict[Hashable, Lock] = {}

    def __init__(self, key: Hashable):
        self._key = key

    async def __aenter__(self):
        if self._key in self._locks:
            lock = self._locks[self._key]
            await lock.acquire()
            self._locks[self._key] = lock
            print(f'Lock {self._key} acquired')
        else:
            self._locks[self._key] = lock = Lock()
            await lock.acquire()
            print(f'Lock {self._key} created and acquired')

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        lock = self._locks[self._key]
        del self._locks[self._key]
        lock.release()
        print(f'Lock {self._key} released')


class Database:
    class Record(BaseModel):
        chat_id: int
        view_id: str
        data: str

    def __init__(self):
        self.__database = {}
        self.__chat_focus_chains = {}

    def insert(self, record_id: uuid.UUID, chat_id: int, view_id: str, data: str, focused: bool = False):
        self.__database[record_id] = self.Record(
            chat_id=chat_id,
            view_id=view_id,
            data=data
        )
        if focused:
            self.focus(record_id)
        print(self.__database)

    def update(self, record_id: uuid.UUID, data: str):
        self.__database[record_id].data = data
        print(self.__database)

    def delete(self, record_id: uuid.UUID):
        del self.__database[record_id]
        self.unfocus(record_id)

    def get(self, record_id: uuid.UUID) -> tuple[str, str]:
        record = self.__database[record_id]
        return record.view_id, record.data

    def focus(self, record_id: uuid.UUID):
        chat_id = self.__database[record_id].chat_id
        self.__chat_focus_chains.setdefault(chat_id, [])
        self.__chat_focus_chains[chat_id].append(record_id)

    def unfocus(self, record_id: uuid.UUID):
        chat_id = self.__database[record_id].chat_id
        try:
            self.__chat_focus_chains[chat_id].remove(record_id)
            if not self.__chat_focus_chains[chat_id]:
                del self.__chat_focus_chains[chat_id]
        except (ValueError, KeyError):
            pass  # It's okay, just ignore that

    def get_focused(self, chat_id: int):
        try:
            return self.__chat_focus_chains[chat_id][-1]
        except (IndexError, KeyError):
            return None


database = Database()


class MessageViewCallback(CallbackData, prefix='v'):
    record_id: uuid.UUID
    """ID of DB record, that stores message and chat data as well 
    as information about message-handling object"""
    action_id: str
    action_args: str


# noinspection Pydantic
class InlineButtonAction(BaseModel):
    action_id: str = None

    const: bool = False
    """ Set to True if action does not change state of the view. Allows action
        to be processed even if the view is not tracked """

    _fn: CallableObject = None

    def __call__(self, fn: Callable):
        if self.action_id is None:
            self.action_id = fn.__name__
        setattr(fn, '__action__', self)
        self._fn = CallableObject(fn)
        return fn

    def call(self, *args, **kwargs):
        return self._fn.call(*args, **kwargs)


# noinspection Pydantic
class MessageView(BaseModel):
    model_config = ConfigDict(extra='forbid')  # Pydantic stuff

    record_id: Optional[uuid.UUID] = Field(init_var=False, default=None)

    message_id: Optional[int] = Field(init_var=False, default=None)
    chat_id: Optional[int] = Field(init_var=False, default=None)

    _view_id: ClassVar[str]
    _track_by_default: bool

    _inline_button_actions: ClassVar[dict[str, Callable]]

    def __init_subclass__(cls, id: str = None, track: bool = None, **kwargs):
        super().__init_subclass__(**kwargs)

        cls._view_id = id if id is not None else cls.__name__

        if cls._view_id in view_table:
            raise  # View with given view_id is already registered

        view_table[cls._view_id] = cls

        # Registering inline keyboard actions -----

        cls._inline_button_actions = {}
        _track = False

        for field in cls.__dict__.values():
            action = getattr(field, '__action__', None)

            if isinstance(action, InlineButtonAction):
                cls._inline_button_actions[field.__action__.action_id] = field
                _track = _track or not action.const  # _track is True if at least one action is not const

        cls._track_by_default = track if track is not None else _track

    def __render__(self):
        return {'text': '😀'}

    async def invoke_inline_button_action(self, action_id: str, kwargs: dict):
        action: InlineButtonAction = getattr(self._inline_button_actions[action_id], '__action__')

        if not action.const and self.record_id is None:
            raise  # Non const actions cannot be processed by non-tracked view

        async with KeyLock(self.record_id):
            await action.call(self, **kwargs)
            await self.refresh()

            if not action.const:
                database.update(self.record_id, self.model_dump_json())

    async def send(self, chat_id: int):
        if self._track_by_default:
            self.record_id = uuid.uuid4()

        self.chat_id = chat_id

        config = self.__render__()
        message = await bot.send_message(chat_id=chat_id, **config)

        self.message_id = message.message_id

        if self._track_by_default:
            database.insert(self.record_id, self.chat_id, self._view_id, self.model_dump_json())

    async def delete(self):
        await bot.delete_message(self.chat_id, self.message_id)
        self.message_id = None
        self.chat_id = None

        database.delete(self.record_id)
        self.record_id = None

    async def refresh(self):
        if self.message_id is None or self.chat_id is None:
            raise  # Cannot refresh message that is not sent

        config = self.__render__()
        try:
            await bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.message_id,
                **config
            )
        except TelegramBadRequest:
            pass


# Table that stores all the views by their view_id
view_table: dict[str, type[MessageView]] = {}


class MyMessageView(MessageView):
    pattern: str
    number: int

    def __render__(self):
        return {
            'text': self.pattern.format_map(self.model_dump()),
            'reply_markup': InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text='-1',
                        callback_data=MessageViewCallback(
                            record_id=self.record_id,
                            action_id='increase',
                            action_args='-1'
                        ).pack()
                    ),
                    InlineKeyboardButton(
                        text='+1',
                        callback_data=MessageViewCallback(
                            record_id=self.record_id,
                            action_id='increase',
                            action_args='1'
                        ).pack()
                    )
                ]]
            )
        }

    @InlineButtonAction()
    async def increase(self, query: CallbackQuery, args: str):
        self.number += int(args)
        await query.answer('Ok!')


async def startup():
    print(view_table)


async def message_handler(message: Message):
    view = MyMessageView(pattern='Counter: {number}', number=0)
    await view.send(message.chat.id)


async def callback_handler(query: CallbackQuery, callback_data: MessageViewCallback):
    view_id, data = database.get(callback_data.record_id)
    view_cls = view_table[view_id]
    view = view_cls.model_validate_json(data)
    await view.invoke_inline_button_action(callback_data.action_id, {
        'query': query,
        'args': callback_data.action_args
    })


dp.startup.register(startup)
dp.message.register(message_handler)
dp.callback_query.register(callback_handler, MessageViewCallback.filter())
dp.run_polling(bot)
