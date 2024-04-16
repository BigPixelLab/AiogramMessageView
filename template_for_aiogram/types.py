import typing
from typing import TypeVar

from aiogram.types import InputFile

T = TypeVar('T')


class TextLayout:
    def __init__(self):
        self._sections: list[str] = []
        self._paragraphs: list[str] = []
        self._words: list[str] = []

    def add_word(self, word: str):
        word = word.strip()
        if not word:
            return
        self._words.append(word)

    def close_paragraph(self):
        paragraph = ' '.join(self._words)
        if not paragraph:
            return
        self._paragraphs.append(paragraph)
        self._words.clear()

    def add_paragraph(self, paragraph: str):
        self.close_paragraph()
        paragraph = paragraph.strip()
        if not paragraph:
            return
        self._paragraphs.append(paragraph)

    def close_section(self):
        self.close_paragraph()
        section = '\n'.join(self._paragraphs)
        if not section:
            return
        self._sections.append(section)
        self._paragraphs.clear()

    def add_section(self, section: str):
        self.close_section()
        section = section.strip()
        if not section:
            return
        self._sections.append(section)

    def close(self) -> str:
        self.close_section()
        return '\n\n'.join(self._sections)


class KeyboardLayout:
    def __init__(self):
        self._rows: list[list] = []
        self._buffer: list = []

    def _close_row(self):
        if not self._buffer:
            return
        self._rows.append(self._buffer)
        self._buffer = []

    def add(self, button):
        self._buffer.append(button)

    def add_row(self, row: list):
        self._close_row()
        self._rows.append(row)

    def result(self) -> list[list]:
        self._close_row()
        return self._rows


def _sub_type(name: str, tp: T) -> T:
    return type(name, (tp,), {})


Text = _sub_type('Text', str)
Paragraph = _sub_type('Paragraph', str)
Section = _sub_type('Section', str)

KeyboardLayoutRow = _sub_type('KeyboardLayoutRow', list)

ImageID = _sub_type('ImageID', str)
AnimationID = _sub_type('AnimationID', str)


class ImageFile(typing.NamedTuple):
    input_file: InputFile


class AnimationFile(typing.NamedTuple):
    input_file: InputFile


__all__ = (
    'TextLayout',
    'KeyboardLayout',
    'Text',
    'Paragraph',
    'Section',
    'KeyboardLayoutRow',
    'ImageID',
    'AnimationID',
    'ImageFile',
    'AnimationFile',
)
