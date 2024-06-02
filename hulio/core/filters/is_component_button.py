from aiogram.types import CallbackQuery

from hulio.core.interfaces.database import IDatabaseController


async def is_component_button(component_id: str, action_id: str, storage: IDatabaseController, prefix: str, sep: str):
    async def _filter(query: CallbackQuery):
        try:
            _prefix, record_id, _action_id, *args = query.data.split(sep)
        except ValueError:
            return False

        if _prefix != prefix:
            return False

        if _action_id != action_id:
            return False

        if component_id != storage.component.get_component_id(record_id):
            return False

        return {
            'component_record_id': record_id,
            'args': args
        }

    return _filter
