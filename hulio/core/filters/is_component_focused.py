from aiogram.types import Message

from hulio.core.interfaces.database import IDatabaseController


def is_component_focused(component_id: str, storage: IDatabaseController):
    async def _filter(message: Message):
        if message.bot is None:
            return False

        focused = storage.get_focused(message.bot.id, message.chat.id, message.from_user.id)

        if focused is None or focused.component_id != component_id:
            return False

        return {
            'component_record_id': focused.component_record_id
        }

    return _filter
