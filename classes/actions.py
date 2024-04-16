import uuid
from contextvars import ContextVar
from typing import Callable, Union, Any, ClassVar, TYPE_CHECKING

from aiogram import Router
from aiogram.types import CallbackQuery, Message
from pydantic import BaseModel

if TYPE_CHECKING:
    from classes.message_view import MessageView

# Temporary router
router = Router()

current_view_record_id = ContextVar('current_view_record_id')

# All views should be registered here
view_id_to_view_map: dict[str, 'MessageView'] = {}


class Action(BaseModel):
    def __call__(self, fn: Callable):
        setattr(fn, '__action__', self)


class MessageSentAction(Action):
    pass


class ButtonPressedAction(Action):
    action_id: str = None
    filter: Callable[[CallbackQuery], Union[dict, bool]] = None

    def __call__(self, fn: Callable):
        if self.action_id is None:
            self.action_id = fn.__name__
        super().__call__(fn)


class TextInputAction(Action):
    filter: Callable[[Message], Union[dict, bool]] = None

    _input_queue: ClassVar[list[uuid.UUID]] = []

    @classmethod
    def input(cls, receiver: Union['MessageView', uuid.UUID] = None):
        if hasattr(receiver, 'record_id'):
            record_id = receiver.record_id
        elif isinstance(receiver, uuid.UUID):
            record_id = receiver
        elif receiver is None:
            record_id = current_view_record_id.get()
        else:
            raise RuntimeError

        cls._input_queue.append(record_id)

    @classmethod
    def update_filter(cls, message: Message) -> Union[dict, bool]:
        if not cls._input_queue:
            return False

        view = MessageView.from_record_id(cls._input_queue[-1])

        return {'view': view}

    @classmethod
    def update_handler(cls, message: Message, view: MessageView):
        pass


router.message.register(
    TextInputAction.update_handler,
    TextInputAction.update_filter
)


class StackReturnedAction(Action):
    filter: Callable[[Any], Union[dict, bool]] = None
