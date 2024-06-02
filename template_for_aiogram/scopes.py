from typing import Generator, Union

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, \
    KeyboardButton

from classes.message_editor import MeMessage, MeMediaType, MeLinkPreview, MePhoto, MeAnimation, MeVideo, MeDocument, \
    MeAudio
from template.dev import *
from .types import *


def document_assembler() -> Generator[MeMessage, MeMessage, None]:
    messages = None

    while (token := (yield)) is not StopParsing:
        if messages is not None:
            raise ParsingCoroutineError('Got unexpected second token')

        elif isinstance(token, MeMessage):
            messages = token
            continue

        raise ParsingCoroutineError(f'Got unexpected token "{token}" (type: {token.__class__})')

    if messages is None:
        raise ParsingCoroutineError('Got no tokens')

    yield messages


DOCUMENT = ParsingScope(document_assembler)


# noinspection DuplicatedCode
def message_assembler() -> Generator[MeMessage,
                                     Union[MeMediaType, Paragraph, Text,
                                           InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove], None]:
    media = None
    text = ''
    reply_markup = None

    layout = TextLayout()

    while (token := (yield)) is not StopParsing:

        if isinstance(token, (MeLinkPreview, MePhoto, MeAnimation, MeVideo, MeDocument, MeAudio)):
            if media is not None:
                raise ParsingCoroutineError('Message cannot have more than one media attached')
            media = token
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
            if reply_markup is not None:
                raise ParsingCoroutineError('Message can only have one keyboard')
            reply_markup = token
            continue

        raise ParsingCoroutineError(f'Got unexpected token "{token}" (type: {token.__class__})')

    text = layout.close()
    yield MeMessage(
        media=media,
        text=text,
        entities=None,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


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
    'MESSAGE',
    'ELEMENT',
    'NO_HTML',
    'INLINE_KEYBOARD',
    'REPLY_KEYBOARD',
    'INLINE_KEYBOARD_ROW',
    'REPLY_KEYBOARD_ROW',
)
