"""
class MessageView
class v, class MessageViewLazyProxy  - solves a cyclic import problem
class Database  - stores system's state


<message disable_web_page_preview="True">
    <!-- Either image, video or link preview -->
    <image src=""/>
    <video src=""/>
    <link-preview href="" size-hint="small"/>

    <section>
        <a href=""> </a>
    </section>

    <inline-keyboard>
        <button> ... </button>
    </inline-keyboard>
</message>


<message>
    <album>
        <image src=""/>
        <image src=""/>
        <image src=""/>
    </album>

    And this is a caption
</message>

"""
import asyncio
import contextvars
import dataclasses
import inspect
import uuid
from asyncio import Lock
from functools import partial
from typing import Optional, ClassVar, Callable, Hashable, Union, Literal, Any

from aiogram import Bot, Dispatcher, F
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, CallbackQuery, ReplyParameters
from pydantic import BaseModel, Field, ConfigDict

import classes.message_editor as me
from template import render, set_default_syntax
from template_for_aiogram import aiogram_syntax

TOKEN = '6786053401:AAGO9mhXYedvc_JVmVuTedDOkPm5dMfIoCI'


bot = Bot(token=TOKEN)
me.bot = bot

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


@dataclasses.dataclass
class CallableObject:
    callback: Callable[..., Any]
    awaitable: bool = dataclasses.field(init=False)
    params: set[str] = dataclasses.field(init=False)
    varkw: bool = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        callback = inspect.unwrap(self.callback)
        self.awaitable = inspect.isawaitable(callback) or inspect.iscoroutinefunction(callback)
        spec = inspect.getfullargspec(callback)
        self.params = {*spec.args, *spec.kwonlyargs}
        self.varkw = spec.varkw is not None

    def _prepare_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        if self.varkw:
            return kwargs

        return {k: kwargs[k] for k in self.params if k in kwargs}

    async def call(self, *args: Any, **kwargs: Any) -> Any:
        wrapped = partial(self.callback, *args, **self._prepare_kwargs(kwargs))
        if self.awaitable:
            return await wrapped()

        loop = asyncio.get_event_loop()
        context = contextvars.copy_context()
        wrapped = partial(context.run, wrapped)
        return await loop.run_in_executor(None, wrapped)


class DatabaseRecord(BaseModel):
    view_id: str
    data: str


class Database:
    def __init__(self):
        self.__database: dict[uuid.UUID, Any] = {}
        self.__chat_focus: dict[tuple[int, int], uuid.UUID] = {}

    def insert(
            self,
            record_id: uuid.UUID,
            view_id: str,
            data: str
    ):
        self.__database[record_id] = DatabaseRecord(
            view_id=view_id,
            data=data
        )

        print(self.__database)

    def update(self, record_id: uuid.UUID, data: str):
        record = self.__database[record_id]
        record.data = data
        print(self.__database)

    def delete(self, record_id: uuid.UUID):
        del self.__database[record_id]

    def get(self, record_id: uuid.UUID) -> tuple[str, str]:
        record = self.__database[record_id]
        return record.view_id, record.data

    def set_focus(self, bot_id: int, chat_id: int, record_id: uuid.UUID):
        self.__chat_focus[bot_id, chat_id] = record_id
        print(f'Focus set to {record_id}!')

    def clear_focus(self, bot_id: int, chat_id: int):
        try:
            del self.__chat_focus[bot_id, chat_id]
        except KeyError:
            pass  # intentional

    def get_focused(self, bot_id: int, chat_id: int) -> Optional[tuple[str, str]]:
        try:
            record_id = self.__chat_focus[bot_id, chat_id]  # May raise KeyError
            record = self.__database[record_id]  # May raise KeyError
        except KeyError:
            return None

        return record.view_id, record.data


database = Database()
set_default_syntax(aiogram_syntax)


# ALL THESE CALLBACKS ARE FOR INTERNAL USE ONLY -----


class SystemActionCallback(CallbackData, prefix='v'):
    """ Informational or general callbacks """
    action: Literal['untracked']


class InlineButtonNoArgsCallback(CallbackData, prefix='v'):
    """ ... """
    record_id: uuid.UUID
    action_id: str


class InlineButtonCallback(CallbackData, prefix='v'):
    """ ... """
    record_id: uuid.UUID
    action_id: str
    action_args: str = ''


# -----


# noinspection Pydantic
class InlineButtonAction(BaseModel):
    action_id: str = None
    fn: CallableObject = Field(init_var=False, default=None)

    def __call__(self, fn: Callable):
        if self.action_id is None:
            self.action_id = fn.__name__
        setattr(fn, '__action__', self)
        self.fn = CallableObject(fn)
        return fn

    def call(self, *args, **kwargs):
        return self.fn.call(*args, **kwargs)


class TextInputAction(BaseModel):
    fn: CallableObject = Field(init_var=False, default=None)

    def __call__(self, fn: Callable):
        setattr(fn, '__action__', self)
        self.fn = CallableObject(fn)
        return fn

    def call(self, *args, **kwargs):
        return self.fn.call(*args, **kwargs)


# Table that stores all the views by their view_id
view_table: dict[str, type['MessageView']] = {}


# noinspection Pydantic
class MessageView(BaseModel):
    model_config = ConfigDict(extra='forbid')  # Pydantic stuff

    record_id: Optional[uuid.UUID] = Field(init_var=False, default=None)
    message: me.MessageEditor = Field(init_var=False, default=None)

    chat_id: Optional[int] = Field(init_var=False, default=None)
    bot_id: Optional[int] = Field(init_var=False, default=None)

    _view_id: ClassVar[str]
    _track_by_default: ClassVar[bool]
    _focus_by_default: ClassVar[bool]

    _inline_buttons: ClassVar[dict[str, InlineButtonAction]]
    _text_inputs: ClassVar[list[TextInputAction]]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # View can only be restored if it is present in the database,
        #   and it is present in the database only if record_id is set.
        #   So on the first initialization record_id will be None, so
        #   we call __created__ method, then view is sent and if it is
        #   tracked record_id is set
        if self.record_id is None:
            self.message = me.MessageEditor()
            self.__created__()

    def __init_subclass__(cls, alias: str = None, track: bool = None, focus: bool = None, **kwargs):
        global view_table

        super().__init_subclass__(**kwargs)

        # Registering view in global table -----

        cls._view_id = alias if alias is not None else cls.__name__

        if cls._view_id in view_table:
            raise  # View with given view_id is already registered

        view_table[cls._view_id] = cls

        # Registering inline keyboard actions -----

        cls._inline_buttons = {}
        cls._text_inputs = []
        _track = False
        _focus = False

        for field in cls.__dict__.values():
            action = getattr(field, '__action__', None)

            if isinstance(action, InlineButtonAction):
                cls._inline_buttons[action.action_id] = action
                _track = True

            if isinstance(action, TextInputAction):
                cls._text_inputs.append(action)
                _track = True
                _focus = True

        cls._track_by_default = (
            track if track is not None
            else _track
        )

        cls._focus_by_default = (
            focus if focus is not None
            else _focus
        )

    def __created__(self):
        """ Overridable. Called first time a view is created (not restored from the database) """
        pass

    def __render__(self, method: Literal['send', 'edit'] = 'send') -> me.MeMessage:
        """ Overridable. Called every time a message needs to be rendered """
        return me.MeMessage(media=None, text='😄', entities=None, parse_mode=None, reply_markup=None)

    async def handle_inline_button(self, action_id: str, kwargs: dict):
        action = self._inline_buttons[action_id]

        async with KeyLock(self.record_id):
            await action.call(self, **kwargs)
            database.update(self.record_id, self.model_dump_json())

    async def handle_text_input(self, kwargs: dict):
        for action in self._text_inputs:
            async with KeyLock(self.record_id):
                await action.call(self, **kwargs)
                await self.refresh()

        database.update(self.record_id, self.model_dump_json())

    async def send(
            self,
            chat_id: Union[int, str],
            message_thread_id: Optional[int] = None,
            disable_notification: Optional[bool] = None,
            protect_content: Optional[bool] = None,
            reply_parameters: Optional[ReplyParameters] = None
    ):
        if self._track_by_default:
            self.record_id = uuid.uuid4()

        self.bot_id = bot.id
        self.chat_id = chat_id

        blueprint = self.__render__()
        await self.message.send(
            message=blueprint,
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
            reply_parameters=reply_parameters
        )
        # message = await bot.send_message(chat_id=chat_id, **config)

        if self._track_by_default:
            database.insert(
                self.record_id,
                self._view_id,
                self.model_dump_json()
            )

        if self._focus_by_default:
            database.set_focus(
                self.bot_id,
                self.chat_id,
                self.record_id
            )

    async def delete(self):
        """ Deletes message and stops tracking view """
        await self.message.delete()

        database.delete(self.record_id)
        self.record_id = None

    async def refresh(self):
        blueprint = self.__render__()
        await self.message.edit(
            message=blueprint
        )

    def focus(self):
        database.set_focus(self.bot_id, self.chat_id, self.record_id)


class TemplateMessageView(MessageView):
    _template: ClassVar[str]

    def __init_subclass__(cls, template: str = None, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._template = template

    def __get_action_callbacks_tracked(self):
        context = {}
        for action_id in self._inline_buttons:
            context[action_id] = InlineButtonNoArgsCallback(
                record_id=self.record_id,
                action_id=action_id
            ).pack()
        return context

    def __get_action_callbacks_untracked(self):
        context = {}
        for action_id in self._inline_buttons:
            context[action_id] = SystemActionCallback(action='untracked').pack()
        return context

    def __context__(self) -> dict[str, Any]:
        context = self.model_dump()
        context['is_tracked'] = is_tracked = self.record_id is not None

        context.update(
            self.__get_action_callbacks_tracked() if is_tracked
            else self.__get_action_callbacks_untracked()
        )

        return context

    def __render__(self, method: Literal['send', 'edit'] = 'send') -> me.MeMessage:
        context = self.__context__()
        return render(self._template, context, syntax=aiogram_syntax)


class MessageViewLazyProxy:
    """
    Initialized with view_id, instantiates view of that type on call.
    To get view class (to call class methods, for example) use `__origin__`
    property

    Example::

        # Here, "MyView" needs "AnotherView" to work, and "AnotherView" needs "MyView".
        # If we imported them in both files, we would get a cyclic import error.

        # file1.py

        AnotherView = v('AnotherView')  # Promise created here

        class MyView(MessageView):
            @InlineButton
            async def _(self):
                view: AnotherView = AnotherView()  # And resolved here

        # file2.py

        MyView = v('MyView')

        class AnotherView(MessageView):
            @InlineButton
            async def _(self):
                view: MyView = MyView()

        # main.py

        import file1
        import file2

    """

    def __init__(self, view_id: str):
        self.__origin_view_id = view_id

    def __call__(self, **kwargs) -> MessageView:
        view_cls: type[MessageView] = view_table[self.__origin_view_id]
        return view_cls(**kwargs)

    @property
    def __origin__(self) -> type[MessageView]:
        return view_table[self.__origin_view_id]


v = MessageViewLazyProxy


# USAGE EXAMPLE -----

async def start_command_handler(message: Message):
    await ViewTest().send(message.chat.id)


class ViewTest(TemplateMessageView, template='test.xml'):
    counter: int = 0

    @InlineButtonAction()
    async def increase(self, args: str):
        self.counter += int(args)
        await self.refresh()


async def startup():
    pass


async def message_handler_filter(message: Message):
    if message.text.startswith('/'):
        return False

    focused = database.get_focused(bot.id, message.chat.id)

    if focused is None:
        return False

    view_id, data = focused
    view_cls = view_table[view_id]
    view = view_cls.model_validate_json(data)

    return {'view': view}


async def message_handler(message: Message, view: MessageView, **kwargs):
    args = {'message': message, **kwargs}
    await view.handle_text_input(args)


async def callback_handler_filter(query: CallbackQuery):
    try:
        callback_data = InlineButtonNoArgsCallback.unpack(query.data)
        args = None
    except (TypeError, ValueError):
        try:
            # noinspection PyUnusedLocal
            callback_data = InlineButtonCallback.unpack(query.data)
            args = callback_data.action_args
        except (TypeError, ValueError):
            return False

    view_id, data = database.get(callback_data.record_id)
    view_cls = view_table[view_id]
    view = view_cls.model_validate_json(data)

    return {
        'view': view,
        'action_id': callback_data.action_id,
        'action_args': args
    }


async def callback_handler(
        query: CallbackQuery,
        view: MessageView,
        action_id: str,
        action_args: str,
        **kwargs
):
    args = {'query': query, 'args': None, **kwargs}
    if action_args is not None:
        args['args'] = action_args

    await view.handle_inline_button(
        action_id,
        args
    )


"""

class MyComponent(Component):
    def __created__(self):
        pass
        
    def __before_sending__(self):
        pass

"""


dp.startup.register(startup)

dp.message.register(message_handler, message_handler_filter)

dp.callback_query.register(callback_handler, callback_handler_filter)

dp.message.register(start_command_handler, F.text == '/start')

dp.run_polling(bot)
