import uuid
import typing as t

from hulio.core.interfaces.database import IDatabaseController, IDatabaseProvider, ComponentRecord, MessageRecord


class DatabaseController(IDatabaseController):
    schema_name = 'hulio'
    component_table_name = 'component'
    message_table_name = 'message'

    def __init__(self, provider: IDatabaseProvider):
        self.provider = provider

    def setup(self):
        self.provider.ensure_schema(self.schema_name)
        self.provider.ensure_table(self.schema_name, self.component_table_name, {
            'record_id': uuid.UUID,
            'parent_record_id': t.Optional[uuid.UUID],
            'message_record_id': uuid.UUID,
            'component_id': str,
            'state_json': str,
            'is_enabled': bool
        })
        self.provider.ensure_table(self.schema_name, self.message_table_name, {
            'record_id': uuid.UUID,
            'bot_id': int,
            'chat_id': int,
            'user_id': int,
            'message_id': int,
            'media_id': str,
            'media_type': str
        })

    def component_track(self, record: ComponentRecord):
        self.provider.insert(self.schema_name, self.component_table_name, record.record_id, {
            'record_id': record.record_id,
            'parent_record_id': record.parent_record_id,
            'message_record_id': record.message_record_id,
            'component_id': record.component_id,
            'state_json': record.state_json,
            'is_enabled': record.is_enabled
        })

    def component_untrack(self, record_id: uuid.UUID):
        message_record_id, = self.provider.get(
            self.schema_name, self.component_table_name,
            record_id,
            columns=['message_record_id']
        )

        self.provider.delete(self.schema_name, self.component_table_name, record_id)

        if self.provider.exists(self.schema_name, self.component_table_name, where={'message_record_id': message_record_id}):
            return

        self.provider.delete(self.schema_name, self.message_table_name, message_record_id)

    def component_update(self, record: ComponentRecord):
        self.provider.update(self.schema_name, self.component_table_name, {
            'parent_record_id': record.parent_record_id,
            'message_record_id': record.message_record_id,
            'state_json': record.state_json,
            'is_enabled': record.is_enabled
        }, record.record_id)

    def component_get_focused(self, bot_id: int, chat_id: int, user_id: int) -> ComponentRecord:
        message_record_id, = self.provider.select(
            self.schema_name, self.message_table_name,
            columns=['record_id'],
            where={'bot_id': bot_id, 'chat_id': chat_id, 'user_id': user_id},
            last_inserted=True
        )

        columns = ['record_id', 'parent_record_id', 'message_record_id', 'component_id', 'state_json', 'is_enabled']
        component = self.provider.select(
            self.schema_name, self.component_table_name,
            columns=columns,
            where={'message_record_id': message_record_id, 'is_enabled': True}
        )

        return ComponentRecord(
            **dict(zip(columns, component))  # dict(zip(['a', 'b'], [1, 2]) -> {'a': 1, 'b': 2}
        )

    def component_get(self, record_id: uuid.UUID) -> ComponentRecord:
        columns = ['record_id', 'parent_record_id', 'message_record_id', 'component_id', 'state_json', 'is_enabled']
        component = self.provider.get(
            self.schema_name, self.component_table_name,
            record_id,
            columns=columns
        )

        return ComponentRecord(
            **dict(zip(columns, component))  # dict(zip(['a', 'b'], [1, 2]) -> {'a': 1, 'b': 2}
        )

    def message_track(self, record: MessageRecord):
        self.provider.insert(self.schema_name, self.message_table_name, record.record_id, {
            'record_id': record.record_id,
            'bot_id': record.bot_id,
            'chat_id': record.chat_id,
            'user_id': record.user_id,
            'message_id': record.message_id,
            'media_id': record.media_id,
            'media_type': record.media_type
        })

    def message_untrack(self, record_id: uuid.UUID):
        component_record_ids = self.provider.select(
            self.schema_name, self.component_table_name,
            columns=['record_id'],
            where={'message_record_id': record_id}
        )

        self.provider.delete(self.schema_name, self.message_table_name, record_id)
        for (component_record_id,) in component_record_ids:
            self.provider.delete(self.schema_name, self.component_table_name, component_record_id)
