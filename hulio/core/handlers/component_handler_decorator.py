import typing as t
import uuid

from aiogram import Bot
from aiogram.types import Message

from hulio.core.classes.callable_object import CallableObject
from hulio.core.classes.component import Component
from hulio.core.classes.component_registry import ComponentRegistry
from hulio.core.contexts import current_component, current_bot
from hulio.core.interfaces.database.i_db_component import IDatabaseComponent
from hulio.core.interfaces.database import IDatabaseController


def _find_bot(bot_id: int, bots: tuple[Bot]) -> t.Optional[Bot]:
    try:
        return next(
            bot
            for bot in bots
            if bot.id == bot_id
        )
    except StopIteration:
        return None


async def component_handler_decorator(handler: t.Callable, storage: IDatabaseController, registry: ComponentRegistry):
    """ Декоратор над обработчиком события в компоненте.
        Handler - должен быть методом компонента.
        Ожидает получить component_record_id из фильтров """

    handler = CallableObject(handler)

    async def _handler(message: Message, component_record_id: uuid.UUID, **kwargs):
        component_info: IDatabaseComponent = storage.component.get(component_record_id)
        component_class: type[Component] = registry.get(component_info.component_id)
        component = component_class.model_validate_json(component_info.model_data_json)

        bot = _find_bot(component.bot_id, kwargs['bots'])

        _current_component = current_component.set(component)
        _current_bot = current_bot.set(bot)

        # Handler - это всегда метод одного из потомков класса Component
        #   поэтому передаём ему component в качестве self
        await handler.call(component, message=message, **kwargs)

        current_component.reset(_current_component)
        current_bot.reset(_current_bot)

    return _handler
