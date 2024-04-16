"""
VIEW CAN BE
- bound to message
    send,  - Sends new message and attaches it to this view
    replace,  - Untracks existing view that has a bound message, and rebinds message to this view
    delete,  - Deletes message and untracks all bound views

    stack,  - Disables existing view that has a bound message, makes it a parent and binds
        its message to self
    pop,  - Untracks this view and enables parent view if there is one

    refresh  - Edits message using view state as a context

- saved in database
    track,  - Adds view's data to the database, that makes it possible for view to react to
        actions
    update,  - Updates view's data in the database
    untrack  - Removes view's state from the database. Disables view as a side effect

- responsive to actions
    enable,  - Enables for tracked view a possibility to react to actions
    disable  - Disables possibility to react to actions but keeps state in the database


"""
import uuid
from typing import ClassVar, Callable, Optional, Type
from contextvars import ContextVar

from aiogram import Bot
from aiogram.exceptions import AiogramError
from aiogram.types import CallbackQuery, Message
from pydantic import BaseModel, Field

from classes.static import ITemplate, IDatabase, database
from classes.actions import ButtonPressedAction


class MessageId(BaseModel):
    bot_token: str
    chat_id: int
    message_id: Optional[int] = None


class MessageView(BaseModel):

    record_id: Optional[uuid.UUID] = Field(init_var=False, default=None)
    """ Used to identify view state in the database """

    message_id: Optional[MessageId] = Field(init_var=False, default=None)
    """ Used to identify message in telegram """

    _view_id: ClassVar[str]
    _template: ClassVar[ITemplate]

    _view_id_view_map: ClassVar[dict[str, Type['MessageView']]] = {}

    _button_pressed_actions_map: ClassVar[dict[str, Callable]] = {}

    # METACLASS STUFF -----------------

    def __init_subclass__(cls, db: IDatabase, template: str, view_id: str = None, **kwargs):
        view_id = view_id if view_id is not None else cls.__name__
        if view_id in cls._view_id_view_map:
            raise
        cls._view_id_view_map[view_id] = cls

        for field in cls.__dict__.values():
            if hasattr(field, '__action__') and isinstance(field.__action__, ButtonPressedAction):
                cls._button_pressed_actions_map[field.__action__.action_id] = field

    # SYSTEM --------------------------

    @classmethod
    def from_record_id(cls, record_id: uuid.UUID) -> 'MessageView':
        model = database.get_view_record(record_id)
        view_cls = cls._view_id_view_map[model.view_id]
        return view_cls.model_validate_json(model.data)

    async def simulate_button_press(self, query: CallbackQuery, action_id: str, args: str):
        if action_id not in self._button_pressed_actions_map:
            raise

        action = self._button_pressed_actions_map[action_id]
        response = await action(self, query, args)

        if isinstance(response, str):
            await query.answer(response)
        else:
            await query.answer()

        # self.refresh()

    async def simulate_text_input(self, message: Message):
        pass

    # ---------------------------------

    def register_bots(self, *bots: Bot, if_registered: Callable[[Bot], None] = None):
        for bot in bots:
            if bot.token not in self._bots:
                self._bots[bot.token] = bot
                continue

            if if_registered is not None:
                if_registered(bot)

    async def send(self, chat_id: int = None, message_thread_id: int = None, bot: Bot = None):
        """ Sends message to the chat. If chat or bot are not specified, sends to current
        chat or bot respectively """

        if self.message_id is not None:
            raise RuntimeError('View is already in use')

        try:
            chat_id = chat_id if chat_id is not None else _context_chat.get()
        except LookupError:
            raise LookupError('There is no chat in current context, specify it in arguments')

        try:
            bot = bot if bot is not None else _context_bot.get()
        except LookupError:
            raise LookupError('There is no bot in current context, specify it in arguments')

        self.register_bots(bot)

        self.message_id = MessageId(
            bot_token=bot.token,
            chat_id=chat_id,
            message_id=None
        )

        config = self.__render__()

        try:
            message = await bot.send_message(
                chat_id=chat_id, message_thread_id=message_thread_id,
                **config,
                reply_to_message_id=None,
                request_timeout=None
            )
        except AiogramError:
            # TODO: Handle that stuff
            raise

        self.message_id.message_id = message.message_id

        self.track()


_context_bot = ContextVar('bot')
_context_chat = ContextVar('chat')
