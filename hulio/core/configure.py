import typing as t

import aiogram

from hulio.core import glob
from hulio.core.attribute import get_attribute
from hulio.core.classes.component_registry import ComponentRegistry
from hulio.core.decorators import TextInfo, ButtonInfo
from hulio.core.filters.is_component_button import is_component_button
from hulio.core.filters.is_component_focused import is_component_focused
from hulio.core.handlers.component_handler_decorator import component_handler_decorator
from hulio.core.interfaces.database import IDatabaseController

if t.TYPE_CHECKING:
    from hulio.core.classes.component import Component


def _register_components_handlers(
        component: Component,
        router: aiogram.Router,
        storage: IDatabaseController,
        registry: ComponentRegistry,
        prefix: str,
        separator: str
):
    """ Регистрирует  """
    component_id = component.get_component_id()

    for handler in component.__dict__.values():
        if not callable(handler):
            continue

        action = get_attribute(handler, 'action')

        if isinstance(action, TextInfo):
            # При получении события, сначала происходит проверка на то находится ли
            # фокус на компоненте нужного типа `is_component_focused`, также
            # получаем record_id компонента в фокусе.
            # Далее в работу вступают пользовательские фильтры `action.filters`.
            # Если всё прошло успешно, `component_handler_decorator` создаёт
            # объект компонента по данным из базы и вызывает на нём обработчик
            router.message.register(
                component_handler_decorator(handler, storage, registry),
                is_component_focused(component_id, storage),
                *action.filters
            )

            continue

        if isinstance(action, ButtonInfo):
            router.callback_query.register(
                component_handler_decorator(handler, storage, registry),
                is_component_button(component_id, action.callback_data_alias, storage, prefix, separator),
                *action.filters
            )

            continue


def configure(
        *,
        aiogram_callback_prefix: str = None,  # 'h' by default
        aiogram_callback_separator: str = None,  # ':' by default
        aiogram_bots: t.Iterable[aiogram.Bot],
        aiogram_router: aiogram.Router,
        storage: IDatabaseController = None,
        components: t.Iterable[Component]
):

    # Filling up bot map
    glob.bot_map = {}
    for bot in aiogram_bots:
        glob.bot_map[bot.id] = bot

    # Setting up storage
    glob.storage = storage

    # Setting up components
    for component in components:
        glob.global_component_registry.register(component)

    # Configuring callback data classes
    if aiogram_callback_prefix is not None:
        glob.aiogram_callback_prefix = aiogram_callback_prefix

    if aiogram_callback_separator is not None:
        glob.aiogram_callback_separator = aiogram_callback_separator

    # Setting up router
    glob.router = aiogram_router

    for component in components:
        _register_components_handlers(
            component,
            glob.router,
            glob.storage,
            glob.global_component_registry,
            glob.aiogram_callback_prefix,
            glob.aiogram_callback_separator
        )

    # if glob.storage is not None:
    #     glob.router.message.register(
    #         ...,
    #         get_message_filter(glob.storage, glob.global_component_registry)
    #     )
