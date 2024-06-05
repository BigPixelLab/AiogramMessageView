import uuid

from hulio.core.interfaces.database import IDatabaseController, IDatabaseProvider, ComponentRecord, MessageRecord


class DatabaseController(IDatabaseController):
    def __init__(self, provider: IDatabaseProvider):
        pass

    def setup(self, provider: IDatabaseProvider):
        raise NotImplementedError

    def component_track(self, record: ComponentRecord):
        raise NotImplementedError

    def component_untrack(self, record_id: uuid.UUID):
        raise NotImplementedError

    def component_update(self, record: ComponentRecord):
        raise NotImplementedError

    def component_get_focused(self, bot_id: int, chat_id: int, user_id: int) -> ComponentRecord:
        raise NotImplementedError

    def component_get(self, record_id: uuid.UUID) -> ComponentRecord:
        raise NotImplementedError

    def message_track(self, record: MessageRecord):
        raise NotImplementedError

    def message_untrack(self, record_id: uuid.UUID):
        raise NotImplementedError
