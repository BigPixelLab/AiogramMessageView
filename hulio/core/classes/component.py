import typing as t
import uuid

from aiogram.exceptions import TelegramAPIError
from aiogram.types import ReplyParameters
from pydantic import BaseModel, Field

from hulio.core.contexts import current_component


class Component(BaseModel):
    _component_id: str

    record_id: t.Optional[uuid.UUID] = Field(init_var=False, default=None)
    parent_record_id: t.Optional[uuid.UUID] = Field(init_var=False, default=None)

    message_record_id: t.Optional[uuid.UUID] = Field(init_var=False, default=None)

    is_detached: t.Optional[bool] = Field(init_var=False, default=None)
    is_enabled: bool = Field(init_var=False, default=True)

    bot_id: int = Field(init_var=False, default=None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __init_subclass__(cls, **kwargs):
        pass

    @property
    def is_tracked(self):
        return self.record_id is not None

    async def send(
            self,

            chat_id: t.Union[int, str],
            message_thread_id: int = None,
            disable_notification: bool = None,
            protect_content: bool = None,
            reply_parameters: ReplyParameters = None,

            detached: bool = False,  # If true, current message keeps being tracked and enabled
            child: bool = False  # New message when closed will be able to return info to this one
    ):
        # Проверяем, не было ли уже отправлено сообщение. Компонент имеет строгую
        # привязку к сообщению, поэтому, если сообщения нет, то нет и компонента
        # в базе
        if self.record_id is not None:
            raise RuntimeError('Cannot resend tracked component')

        # Если caller s None, значит компонент отправляется не из обработчика
        # другого компонента
        caller: t.Optional[Component] = current_component.get(None)

        # Единственный случай когда отключенный или не отслеживаемый компонент
        # пытается отправить сообщение - это когда он уже отправлял и его
        # отключили. Статические сообщения не имеют обработчиков, в которых
        # можно что-либо отправлять
        if caller is not None and not caller.is_enabled:
            raise RuntimeError('Disabled or not tracked components cannot send')

        # Не можем установить компонент как дочерний, если нет родителя
        if child and caller is None:
            raise RuntimeError('Component can be set as child only from another components handler')

        _parent = None

        if child:
            _parent = caller

            if not detached:
                await caller.__disable()

        if not child and not detached and caller is not None:
            # If called from aiogram handler, then there is no component to untrack
            await caller.__untrack()

        if not self._is_static:
            _record_id = uuid.uuid4()
        else:
            _record_id = None

        context = {
            'record_id': _record_id,
            'chat_id': chat_id,
            'message_thread_id': message_thread_id,
            'reply_parameters': reply_parameters
        }

        _message = self.__render__(context)

        try:
            message = await self.message.send(
                message=_message,
                chat_id=chat_id,
                message_thread_id=message_thread_id,
                disable_notification=disable_notification,
                protect_content=protect_content,
                reply_parameters=reply_parameters
            )
        except TelegramAPIError as error:
            self.__unable_send__(error)
            return

        if not self._is_static:
            await self.__track(self.record_id)

        if not self._is_static and self._focus_by_default:
            await self.__focus()

    @classmethod
    def get_component_id(cls):
        return cls._component_id


# class Component(BaseModel):
#     _component_id: t.ClassVar[str]
#
#     _is_static: t.ClassVar[bool]
#     _focus_by_default: t.ClassVar[bool]
#     _refresh_on_toggle: t.ClassVar[bool]
#
#     record_id: t.Optional[uuid.UUID]
#     message: me.MessageManager = Field(init_var=False, default_factory=me.MessageManager)
#
#     def __init_subclass__(
#             cls,
#             registry: 'ComponentRegistry' = None,
#             alias: str = None,
#             refresh_on_toggle: bool = None,  # To call refresh on enable or disable (ex. to toggle the keyboard)
#             **kwargs
#     ):
#         super().__init_subclass__(**kwargs)
#
#         if alias is not None:
#             cls._component_id = alias
#         else:
#             cls._component_id = cls.__name__
#
#         global_component_registry.register(
#             cls._component_id,
#             cls
#         )
#
#         if registry is not None:
#             registry.register(
#                 cls._component_id,
#                 cls
#             )
#
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#
#         if self.record_id is None:
#             self.__created__()
#
#     def __del__(self):
#         if self.record_id is None:
#             self.__destroyed__()
#
#         super().__del__()
#
#     # Overridable methods -------------
#
#     def __created__(self):
#         pass
#
#     def __destroyed__(self):
#         pass
#
#     def __render__(self, context: dict[str, t.Any]) -> me.Message:
#         # Этот контекст позже можно будет передавать в __context__, где
#         # он будет либо полностью перезаписываться, либо дополняться
#         pass
#
#     def __unable_send__(self, exception: TelegramAPIError):
#         raise exception
#
#     def __unable_refresh__(self, exception: TelegramAPIError):
#         raise exception
#
#     # ---------------------------------
#
#     @classmethod
#     def get_component_id(cls):
#         return cls._component_id
#
#     async def __call_action(self):
#         # Setting up context for an action
#         _calling_component = calling_component.set(self)
#
#         # Action called here...
#
#         calling_component.reset(_calling_component)
#
#     async def __disable(self):
#         pass
#
#     async def __track(self, record_id: uuid.UUID = None):
#         pass
#
#     async def __untrack(self):
#         pass
#
#     async def __focus(self):
#         pass
#
#     async def send(
#             self,
#
#             chat_id: t.Union[int, str],
#             message_thread_id: int = None,
#             disable_notification: bool = None,
#             protect_content: bool = None,
#             reply_parameters: ReplyParameters = None,
#
#             detached: bool = False,  # If true, current message keeps being tracked and enabled
#             child: bool = False  # New message when closed will be able to return info to this one
#     ):
#         # Проверяем, не было ли уже отправлено сообщение. Компонент имеет строгую
#         # привязку к сообщению, поэтому, если сообщения нет, то нет и компонента
#         # в базе
#         if self.record_id is not None:
#             raise RuntimeError('Cannot resend tracked component')
#
#         caller: t.Optional[Component] = calling_component.get(None)
#
#         if caller is not None and caller.record_id is not None:
#             caller_db: t.Optional[IDatabaseComponent] = database.component.get(caller.record_id)
#         else:
#             caller_db: t.Optional[IDatabaseComponent] = None
#
#         # Единственный случай когда отключенный или не отслеживаемый компонент
#         # пытается отправить сообщение - это когда он уже отправлял и его
#         # отключили. Статические сообщения не имеют обработчиков, в которых
#         # можно что-либо отправлять
#         if caller is not None and (caller_db is None or not caller_db.is_enabled):
#             raise RuntimeError('Disabled or not tracked components cannot send nothing')
#
#         # Не можем установить компонент как дочерний, если нет родителя
#         if child and caller is None:
#             raise RuntimeError('Component can be set as child only from another components handler')
#
#         _parent = None
#
#         if child:
#             _parent = caller
#
#             if not detached:
#                 await caller.__disable()
#
#         if not child and not detached and caller is not None:
#             # If called from aiogram handler, then there is no component to untrack
#             await caller.__untrack()
#
#         if not self._is_static:
#             _record_id = uuid.uuid4()
#         else:
#             _record_id = None
#
#         context = {
#             'record_id': _record_id,
#             'chat_id': chat_id,
#             'message_thread_id': message_thread_id,
#             'reply_parameters': reply_parameters
#         }
#
#         _message = self.__render__(context)
#
#         try:
#             message = await self.message.send(
#                 message=_message,
#                 chat_id=chat_id,
#                 message_thread_id=message_thread_id,
#                 disable_notification=disable_notification,
#                 protect_content=protect_content,
#                 reply_parameters=reply_parameters
#             )
#         except TelegramAPIError as error:
#             self.__unable_send__(error)
#             return
#
#         if not self._is_static:
#             await self.__track(self.record_id)
#
#         if not self._is_static and self._focus_by_default:
#             await self.__focus()
#
#     async def replace(
#             self,
#             child: bool = False  # New message when closed will be able to return info to this one
#     ):
#         try:
#             caller: Component = calling_component.get()
#         except LookupError:
#             raise LookupError('Component can be replaced only from another components handler')
#
#         self.message = caller.message.copy()
#
#     async def close(self, data: t.Any = None, keep_message: bool = False):
#         pass
#
#     async def refresh(self, keep_media: bool = False):
#         pass
#
#     async def save(self):
#         pass


__all__ = (
    'Component',
)
