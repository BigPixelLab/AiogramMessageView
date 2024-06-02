from typing import Optional, Literal, Union, Protocol, Any

import aiogram.types as tg
from aiogram import Bot
from pydantic import BaseModel, ConfigDict, Field


# noinspection PyPropertyDefinition
class IMediaType(Protocol):
    @property
    def media(self) -> Any:
        ...

    @property
    def media_type(self) -> str:
        ...


class LinkPreview(BaseModel):
    url: str
    size_hint: Optional[Literal['small', 'large']]
    position: Optional[Literal['above', 'below']]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def media(self) -> Any:
        return None

    @property
    def media_type(self) -> str:
        return 'lp'


class Photo(BaseModel):
    photo: Union[tg.InputFile, str]
    has_spoiler: Optional[bool]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def media(self):
        return self.photo

    @property
    def media_type(self):
        return 'p'


class Animation(BaseModel):
    animation: Union[tg.InputFile, str]
    duration: Optional[int]
    width: Optional[int]
    height: Optional[int]
    thumbnail: Optional[tg.InputFile]
    has_spoiler: Optional[bool]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def media(self):
        return self.animation

    @property
    def media_type(self):
        return 'a'


class Video(BaseModel):
    video: Union[tg.InputFile, str]
    duration: Optional[int]
    width: Optional[int]
    height: Optional[int]
    thumbnail: Optional[tg.InputFile]
    has_spoiler: Optional[bool]
    supports_streaming: Optional[bool]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def media(self):
        return self.video

    @property
    def media_type(self):
        return 'v'


class Document(BaseModel):
    document: Union[tg.InputFile, str]
    thumbnail: Optional[tg.InputFile]
    disable_content_type_detection: Optional[bool]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def media(self):
        return self.document

    @property
    def media_type(self):
        return 'd'


class Audio(BaseModel):
    audio: Union[tg.InputFile, str]
    duration: Optional[int]
    performer: Optional[str]
    title: Optional[str]
    thumbnail: Optional[tg.InputFile]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def media(self):
        return self.audio

    @property
    def media_type(self):
        return 'au'


MediaType = Union[LinkPreview, Photo, Animation, Video, Document, Audio]


class Message(BaseModel):
    media: Optional[MediaType]
    text: str
    entities: Optional[list[tg.MessageEntity]]
    parse_mode: Optional[str]
    reply_markup: Optional[Union[
        tg.InlineKeyboardMarkup,
        tg.ReplyKeyboardMarkup,
        tg.ReplyKeyboardRemove,
        tg.ForceReply
    ]]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class MessageManager(BaseModel):
    """
    Класс для упрощённой отправки и редактирования сообщений.
    Сохраняет необходимую дальнейшего редактирования информацию при отправке.

    Решение о том необходимо ли редактировать медиа производится следующим образом:
    - Медиа представлено как url или file_id и url или file_id изменились
    - Медиа представлено как InputFile и filename изменился
    - Или параметр force_edit_media установлен на True
    """

    media_type: Optional[Literal[
        'nm',  # No media
        'lp',  # LinkPreview
        'p',  # Photo
        'a',  # Animation
        'v',  # Video
        'd',  # Document
        'au'  # Audio
    ]] = Field(init_var=False, default=None)
    media_id: Optional[str] = Field(init_var=False, default=None)  # url, file_id or filename
    is_input_file: Optional[bool] = Field(init_var=False, default=None)  # If true, media_id is filename

    chat_id: Optional[Union[int, str]] = Field(init_var=False, default=None)
    message_id: Optional[int] = Field(init_var=False, default=None)

    def _set_media_id(self, media: Union[tg.InputFile, str]) -> None:
        if isinstance(media, tg.InputFile):
            self.media_id = media.filename
            self.is_input_file = True
        elif isinstance(media, str):
            self.media_id = media
            self.is_input_file = False
        else:
            raise TypeError('Invalid media')

    def _is_media_needs_to_be_edited(self, media: Optional[IMediaType]):
        if self.media_type != media.media_type:
            return True

        is_input_file = isinstance(media.media, tg.InputFile)

        if is_input_file != self.is_input_file:
            return True

        if is_input_file:
            return media.media.filename != self.media_id

        return media.media != self.media_id

    async def send(
            self,
            bot: Bot,
            message: Message,
            chat_id: Union[int, str],
            message_thread_id: Optional[int] = None,
            disable_notification: Optional[bool] = None,
            protect_content: Optional[bool] = None,
            reply_parameters: Optional[tg.ReplyParameters] = None
    ) -> tg.Message:
        parameters = {
            'chat_id': chat_id,
            'message_thread_id': message_thread_id,
            'disable_notification': disable_notification,
            'protect_content': protect_content,
            'reply_parameters': reply_parameters
        }

        if message.media is None:
            self.media_type = 'nm'

            telegram_message = await bot.send_message(
                link_preview_options=tg.LinkPreviewOptions(
                    is_disabled=True
                ),

                text=message.text,
                entities=message.entities,
                parse_mode=message.parse_mode,
                reply_markup=message.reply_markup,
                **parameters
            )

        elif isinstance(message.media, LinkPreview):
            self.media_type = 'lp'

            # noinspection DuplicatedCode
            telegram_message = await bot.send_message(
                link_preview_options=tg.LinkPreviewOptions(
                    is_disabled=False,
                    url=message.media.url,
                    prefer_small_media=(
                        None if message.media.size_hint is None
                        else message.media.size_hint == 'small'
                    ),
                    prefer_large_media=(
                        None if message.media.size_hint is None
                        else message.media.size_hint == 'large'
                    ),
                    show_above_text=(
                        None if message.media.position is None
                        else message.media.position == 'above'
                    ),
                ),

                text=message.text,
                entities=message.entities,
                parse_mode=message.parse_mode,
                reply_markup=message.reply_markup,
                **parameters
            )

        elif isinstance(message.media, Photo):
            self.media_type = 'p'
            self._set_media_id(message.media.photo)

            telegram_message = await bot.send_photo(
                photo=message.media.photo,
                has_spoiler=message.media.has_spoiler,

                caption=message.text,
                caption_entities=message.entities,
                parse_mode=message.parse_mode,
                reply_markup=message.reply_markup,
                **parameters
            )

        elif isinstance(message.media, Animation):
            self.media_type = 'a'
            self._set_media_id(message.media.animation)

            telegram_message = await bot.send_animation(
                animation=message.media.animation,
                duration=message.media.duration,
                width=message.media.width,
                height=message.media.height,
                thumbnail=message.media.thumbnail,
                has_spoiler=message.media.has_spoiler,

                caption=message.text,
                caption_entities=message.entities,
                parse_mode=message.parse_mode,
                reply_markup=message.reply_markup,
                **parameters
            )

        elif isinstance(message.media, Video):
            self.media_type = 'v'
            self._set_media_id(message.media.video)

            telegram_message = await bot.send_video(
                video=message.media.video,
                duration=message.media.duration,
                width=message.media.width,
                height=message.media.height,
                thumbnail=message.media.thumbnail,
                has_spoiler=message.media.has_spoiler,
                supports_streaming=message.media.supports_streaming,

                caption=message.text,
                caption_entities=message.entities,
                parse_mode=message.parse_mode,
                reply_markup=message.reply_markup,
                **parameters
            )

        elif isinstance(message.media, Document):
            self.media_type = 'd'
            self._set_media_id(message.media.document)

            telegram_message = await bot.send_document(
                document=message.media.document,
                thumbnail=message.media.thumbnail,
                disable_content_type_detection=message.media.disable_content_type_detection,

                caption=message.text,
                caption_entities=message.entities,
                parse_mode=message.parse_mode,
                reply_markup=message.reply_markup,
                **parameters
            )

        elif isinstance(message.media, Audio):
            self.media_type = 'au'
            self._set_media_id(message.media.audio)

            telegram_message = await bot.send_audio(
                audio=message.media.audio,
                duration=message.media.duration,
                performer=message.media.performer,
                title=message.media.title,
                thumbnail=message.media.thumbnail,

                caption=message.text,
                caption_entities=message.entities,
                parse_mode=message.parse_mode,
                reply_markup=message.reply_markup,
                **parameters
            )

        else:
            raise NotImplementedError('Unknown media type')

        self.chat_id = telegram_message.chat.id
        self.message_id = telegram_message.message_id

        return telegram_message

    async def edit(
            self,
            bot: Bot,
            message: Message,
            force_edit_media: bool = False
    ) -> Union[tg.Message, bool]:
        parameters = {
            'chat_id': self.chat_id,
            'message_id': self.message_id,
            'inline_message_id': None
        }

        if self.media_type in ('nm', 'lp') and message.media is None:
            self.media_type = 'nm'  # TODO: This things should go after edit or send, so in case fo an error MessageEditor would be clear

            return await bot.edit_message_text(
                link_preview_options=tg.LinkPreviewOptions(
                    is_disabled=False
                ),

                text=message.text,
                entities=message.entities,
                parse_mode=message.parse_mode,
                reply_markup=message.reply_markup,
                **parameters
            )

        if self.media_type in ('nm', 'lp') and isinstance(message.media, LinkPreview):
            self.media_type = 'lp'

            # noinspection DuplicatedCode
            return await bot.edit_message_text(
                link_preview_options=tg.LinkPreviewOptions(
                    is_disabled=False,
                    url=message.media.url,
                    prefer_small_media=(
                        None if message.media.size_hint is None
                        else message.media.size_hint == 'small'
                    ),
                    prefer_large_media=(
                        None if message.media.size_hint is None
                        else message.media.size_hint == 'large'
                    ),
                    show_above_text=(
                        None if message.media.position is None
                        else message.media.position == 'above'
                    ),
                ),

                text=message.text,
                entities=message.entities,
                parse_mode=message.parse_mode,
                reply_markup=message.reply_markup,
                **parameters
            )

        # Message with no media can only be edited to have LinkPreview
        if self.media_type in ('nm', 'lp'):
            raise ValueError(
                'There is no media in the message to edit. '
                'Message without media can only be edited to have a link preview'
            )

        # Media cannot be removed, except cases above, so we just keep it
        if message.media is not None:
            edit_media = force_edit_media or self._is_media_needs_to_be_edited(message.media)
        else:
            edit_media = False

        if not edit_media:
            return await bot.edit_message_caption(
                caption=message.text,
                caption_entities=message.entities,
                parse_mode=message.parse_mode,
                reply_markup=message.reply_markup,
                **parameters
            )

        if isinstance(message.media, Photo):
            self.media_type = 'p'
            self._set_media_id(message.media.photo)

            return await bot.edit_message_media(
                media=tg.InputMediaPhoto(
                    media=message.media.photo,
                    has_spoiler=message.media.has_spoiler,
                    caption=message.text,
                    caption_entities=message.entities,
                    parse_mode=message.parse_mode
                ),
                reply_markup=message.reply_markup,
                **parameters
            )

        if isinstance(message.media, Animation):
            self.media_type = 'a'
            self._set_media_id(message.media.animation)

            return await bot.edit_message_media(
                media=tg.InputMediaAnimation(
                    media=message.media.animation,
                    thumbnail=message.media.thumbnail,
                    width=message.media.width,
                    height=message.media.height,
                    duration=message.media.duration,
                    has_spoiler=message.media.has_spoiler,
                    caption=message.text,
                    caption_entities=message.entities,
                    parse_mode=message.parse_mode
                ),
                reply_markup=message.reply_markup,
                **parameters
            )

        if isinstance(message.media, Video):
            self.media_type = 'v'
            self._set_media_id(message.media.video)

            return await bot.edit_message_media(
                media=tg.InputMediaVideo(
                    media=message.media.video,
                    thumbnail=message.media.thumbnail,
                    width=message.media.width,
                    height=message.media.height,
                    duration=message.media.duration,
                    supports_streaming=message.media.supports_streaming,
                    has_spoiler=message.media.has_spoiler,
                    caption=message.text,
                    caption_entities=message.entities,
                    parse_mode=message.parse_mode
                ),
                reply_markup=message.reply_markup,
                **parameters
            )

        if isinstance(message.media, Document):
            self.media_type = 'd'
            self._set_media_id(message.media.document)

            return await bot.edit_message_media(
                media=tg.InputMediaDocument(
                    media=message.media.document,
                    thumbnail=message.media.thumbnail,
                    disable_content_type_detection=message.media.disable_content_type_detection,
                    caption=message.text,
                    caption_entities=message.entities,
                    parse_mode=message.parse_mode
                ),
                reply_markup=message.reply_markup,
                **parameters
            )

        if isinstance(message.media, Audio):
            self.media_type = 'au'
            self._set_media_id(message.media.audio)

            return await bot.edit_message_media(
                media=tg.InputMediaAudio(
                    media=message.media.audio,
                    thumbnail=message.media.thumbnail,
                    duration=message.media.duration,
                    performer=message.media.performer,
                    title=message.media.title,
                    caption=message.text,
                    caption_entities=message.entities,
                    parse_mode=message.parse_mode
                ),
                reply_markup=message.reply_markup,
                **parameters
            )

        raise NotImplementedError('Unknown media type')

    async def delete(self, bot: Bot):
        if await bot.delete_message(self.chat_id, self.message_id):
            self.__init__()
            return True
        return False


__all__ = (
    'IMediaType',
    'LinkPreview',
    'Photo',
    'Animation',
    'Video',
    'Document',
    'Audio',
    'Message',
    'MessageManager'
)
