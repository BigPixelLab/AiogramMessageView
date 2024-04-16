from typing import Generator, Union

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, \
    KeyboardButton

from template.dev import *
from .types import *


def document_assembler() -> Generator[MessageRenderList, Union[MessageRenderList, MessageRender], None]:
    messages = None

    while (token := (yield)) is not StopParsing:
        if messages is not None:
            raise ParsingCoroutineError('Got unexpected second token')

        elif isinstance(token, MessageRenderList):
            messages = token
            continue

        elif isinstance(token, MessageRender):
            messages = MessageRenderList([token])
            continue

        raise ParsingCoroutineError(f'Got unexpected token "{token}" (type: {token.__class__})')

    if messages is None:
        raise ParsingCoroutineError('Got no tokens')

    yield messages


DOCUMENT = ParsingScope(document_assembler)


# noinspection DuplicatedCode
def message_assembler() -> Generator[MessageRender,
                                     Union[ImageID, ImageFile, AnimationID, AnimationFile, Paragraph, Text,
                                           InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove], None]:
    message = MessageRender("")
    layout = TextLayout()

    while (token := (yield)) is not StopParsing:

        if isinstance(token, ImageID):
            if message.photo is not None:
                raise ParsingCoroutineError('Message can only have one photo')
            if message.animation is not None:
                raise ParsingCoroutineError('Message can not have both photo and animation')
            message.photo = token
            continue

        if isinstance(token, ImageFile):
            if message.photo is not None:
                raise ParsingCoroutineError('Message can only have one photo')
            if message.animation is not None:
                raise ParsingCoroutineError('Message can not have both photo and animation')
            message.photo = token.input_file
            continue

        if isinstance(token, AnimationID):
            if message.animation is not None:
                raise ParsingCoroutineError('Message can only have one animation')
            if message.photo is not None:
                raise ParsingCoroutineError('Message can not have both photo and animation')
            message.animation = token
            continue

        if isinstance(token, AnimationFile):
            if message.animation is not None:
                raise ParsingCoroutineError('Message can only have one animation')
            if message.photo is not None:
                raise ParsingCoroutineError('Message can not have both photo and animation')
            message.animation = token.input_file
            continue

        if isinstance(token, Section):
            layout.add_section(token)
            continue

        if isinstance(token, Paragraph):
            layout.add_paragraph(token)
            continue

        if isinstance(token, (Text, str)):
            layout.add_word(token)
            continue

        if isinstance(token, (InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove)):
            if message.keyboard is not None:
                raise ParsingCoroutineError('Message can only have one keyboard')
            message.keyboard = token
            continue

        raise ParsingCoroutineError(f'Got unexpected token "{token}" (type: {token.__class__})')

    message.text = layout.close()
    yield message


MESSAGE = ParsingScope(message_assembler)


# noinspection DuplicatedCode
def text_assembler() -> Generator[str, Union[Paragraph, Text], None]:
    layout = TextLayout()

    while (token := (yield)) is not StopParsing:

        if isinstance(token, Section):
            layout.add_section(token)
            continue

        if isinstance(token, Paragraph):
            layout.add_paragraph(token)
            continue

        if isinstance(token, (Text, str)):
            layout.add_word(token)
            continue

        raise ParsingCoroutineError(f'Got unexpected token "{token}" (type: {token.__class__})')

    yield layout.close()


ELEMENT = ParsingScope(text_assembler)
NO_HTML = ParsingScope(text_assembler)


def keyboard_assembler() -> Generator[Union[list[list[InlineKeyboardButton]], list[list[KeyboardButton]]],
                                      Union[InlineKeyboardButton, KeyboardButton], None]:
    layout = KeyboardLayout()

    while (token := (yield)) is not StopParsing:

        if isinstance(token, KeyboardLayoutRow):
            layout.add_row(token)
            continue

        if isinstance(token, (InlineKeyboardButton, KeyboardButton)):
            layout.add(token)
            continue

        raise ParsingCoroutineError(f'Got unexpected token "{token}" (type: {token.__class__})')

    yield layout.result()


INLINE_KEYBOARD = ParsingScope(keyboard_assembler)
REPLY_KEYBOARD = ParsingScope(keyboard_assembler)


def keyboard_row_assembler() -> Generator[KeyboardLayoutRow, Union[InlineKeyboardButton, KeyboardButton], None]:
    buttons = KeyboardLayoutRow()

    while (token := (yield)) is not StopParsing:

        if isinstance(token, (InlineKeyboardButton, KeyboardButton)):
            buttons.append(token)
            continue

        raise ParsingCoroutineError(f'Got unexpected token "{token}" (type: {token.__class__})')

    yield buttons


INLINE_KEYBOARD_ROW = ParsingScope(keyboard_row_assembler)
REPLY_KEYBOARD_ROW = ParsingScope(keyboard_row_assembler)


__all__ = (
    'DOCUMENT',
    'MESSAGES',
    'MESSAGE',
    'ELEMENT',
    'NO_HTML',
    'INLINE_KEYBOARD',
    'REPLY_KEYBOARD',
    'INLINE_KEYBOARD_ROW',
    'REPLY_KEYBOARD_ROW',
)
