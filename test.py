from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage

import hulio.core.configure

TOKEN = '6786053401:AAGO9mhXYedvc_JVmVuTedDOkPm5dMfIoCI'

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class CounterComponent(hulio.TemplateComponent, template='...'):
    counter: int

    @hulio.button
    def add(self):
        self.counter += 1
        self.refresh()


@dp.message(CommandStart(deep_link=False))
async def command_start(message: Message, command: CommandObject):
    await CounterComponent(counter=0).send(message.chat.id)


hulio.configure(
    aiogram_bots=[bot],  # Для работы hulio нужно иметь список всех ботов, через которые могут отправляться компоненты
    aiogram_router=dp,  # Роутер в котором будут регистрироваться обработчики
    storage=MemoryStorage(),
    components=[
        CounterComponent
    ]
)

dp.run_polling(bot)
