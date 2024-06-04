import uuid
from pprint import pprint

from hulio.core.providers.memory import MemoryStorageProvider

p = MemoryStorageProvider()
p.ensure_schema('test')
p.ensure_table('test', 'table', {'col1': str, 'col2': str, 'col3': str})

p.insert('test', 'table', record1 := uuid.uuid4(), {'col1': 'Hello', 'col3': '!', 'col2': 'World'})
p.insert('test', 'table', uuid.uuid4(), {'col1': '1', 'col2': '2', 'col3': '3'})
p.insert('test', 'table', uuid.uuid4(), {'col1': 'jtr', 'col2': 'fwe', 'col3': 'ryj'})

pprint(p._database)

rows = p.select('test', 'table', ['col1'], last_inserted=True)
pprint(rows)

p.update('test', 'table', {'col3': '?'}, record1)
rows = p.select('test', 'table')
pprint(rows)
