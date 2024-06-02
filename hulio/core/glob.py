import typing as t

import aiogram

from hulio.core.classes.component_registry import ComponentRegistry
from hulio.core.interfaces.database import IDatabaseController

aiogram_callback_prefix: str = 'h'
aiogram_callback_separator: str = ':'

storage: t.Optional[IDatabaseController] = None
router: t.Optional[aiogram.Router] = None

global_component_registry = ComponentRegistry(
    debug_name='Global Component Registry'
)
v = global_component_registry.get_lazy

# BotID to Bot object mapping
bot_map: dict[int, aiogram.Bot] = {}

__all__ = (
    'router',
    'global_component_registry',
    'v'
)
