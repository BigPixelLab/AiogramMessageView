from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from hulio.core.classes.component import Component
from hulio.core.configure import configure
from hulio.core.decorators import button
from hulio.core.providers.memory import MemoryStorageProvider

TOKEN = '6786053401:AAGO9mhXYedvc_JVmVuTedDOkPm5dMfIoCI'

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class CounterComponent(Component, template='test.xml'):
    counter: int

    @button
    def add(self):
        self.counter += 1
        self.refresh()


@dp.message(CommandStart(deep_link=False))
async def command_start(message: Message):
    await CounterComponent(counter=0).send(message.chat.id)


configure(
    aiogram_bots=[bot],  # Для работы hulio нужно иметь список всех ботов, через которые могут отправляться компоненты
    aiogram_router=dp,  # Роутер в котором будут регистрироваться обработчики
    storage_provider=MemoryStorageProvider(),
    components=[
        CounterComponent
    ]
)

dp.run_polling(bot)
