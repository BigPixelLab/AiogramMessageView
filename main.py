from aiogram.types import Message, CallbackQuery

from classes.message_view import MessageView
from classes.actions import ButtonPressedAction, TextInputAction, StackReturnedAction, MessageSentAction


# USAGE EXAMPLE --------------------------


class GreetingMessage(MessageView, template='...'):
    @ButtonPressedAction()
    async def begin(self, _):
        await RegistrationFormMessage().send(self.chat_id, self.message_thread_id)
        await self.untrack()


class RegistrationFormMessage(MessageView, template='...'):
    state: str = 'firstname'
    error: str = None

    firstname: str = None
    age: int = None

    @MessageSentAction()
    async def sent(self):
        pass

    @TextInputAction()
    async def firstname_input_action(self, text: str):
        self.firstname = text[:100]
        self.state = 'age'

    @TextInputAction()
    async def age_input_action(self, text: str):
        try:
            self.age = int(text[:100])
            self.state = 'confirm'
        except ValueError:
            self.error = 'Age must be a number'

    @ButtonPressedAction()
    async def confirm(self, _):
        self.state = 'done'
        await self.refresh()
        await self.untrack()


# USAGE EXAMPLE --------------------------


class RegistrationMessage(MessageView, template=''):
    firstname: str = None
    lastname: str = None

    @ButtonPressedAction(action_id='firstname')
    async def edit_firstname(self, _):
        await TextInputMessage(caption='Enter your firstname', tag='firstname').stack(self)

    @ButtonPressedAction(action_id='lastname')
    async def edit_lastname(self, _):
        await TextInputMessage(caption='Enter your lastname', tag='lastname').stack(self)

    @StackReturnedAction(filter=lambda val: 'firstname' in val)
    async def firstname_entered(self, data: dict):
        self.firstname = data['firstname']

    @StackReturnedAction(filter=lambda val: 'lastname' in val)
    async def lastname_entered(self, data: dict):
        self.lastname = data['lastname']


class TextInputMessage(MessageView, template=''):
    caption: str
    tag: str
    text: str = None

    @TextInputAction()
    async def input(self, message: Message):
        self.text = message.text
        await message.delete()

    @ButtonPressedAction()
    async def confirm(self, _):
        await self.pop({self.tag: self.text})

