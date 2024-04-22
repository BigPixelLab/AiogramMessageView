from typing import Optional, Literal, Union, Protocol, Any

from aiogram.types import InputFile, MessageEntity, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, \
    ForceReply, ReplyParameters, LinkPreviewOptions, Message, InputMediaPhoto, InputMediaAnimation, InputMediaVideo, \
    InputMediaDocument, InputMediaAudio
from pydantic import BaseModel, ConfigDict

bot = ...


# noinspection PyPropertyDefinition
class IMediaType(Protocol):
    @property
    def media(self) -> Any:
        ...

    @property
    def media_type(self) -> str:
        ...


class MeLinkPreview(BaseModel):
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


class MePhoto(BaseModel):
    photo: Union[InputFile, str]
    has_spoiler: Optional[bool]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def media(self):
        return self.photo

    @property
    def media_type(self):
        return 'p'


class MeAnimation(BaseModel):
    animation: Union[InputFile, str]
    duration: Optional[int]
    width: Optional[int]
    height: Optional[int]
    thumbnail: Optional[InputFile]
    has_spoiler: Optional[bool]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def media(self):
        return self.animation

    @property
    def media_type(self):
        return 'a'


class MeVideo(BaseModel):
    video: Union[InputFile, str]
    duration: Optional[int]
    width: Optional[int]
    height: Optional[int]
    thumbnail: Optional[InputFile]
    has_spoiler: Optional[bool]
    supports_streaming: Optional[bool]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def media(self):
        return self.video

    @property
    def media_type(self):
        return 'v'


class MeDocument(BaseModel):
    document: Union[InputFile, str]
    thumbnail: Optional[InputFile]
    disable_content_type_detection: Optional[bool]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def media(self):
        return self.document

    @property
    def media_type(self):
        return 'd'


class MeAudio(BaseModel):
    audio: Union[InputFile, str]
    duration: Optional[int]
    performer: Optional[str]
    title: Optional[str]
    thumbnail: Optional[InputFile]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def media(self):
        return self.audio

    @property
    def media_type(self):
        return 'au'


MeMediaType = Union[MeLinkPreview, MePhoto, MeAnimation, MeVideo, MeDocument, MeAudio]


class MeMessage(BaseModel):
    media: Optional[MeMediaType]
    text: str
    entities: Optional[list[MessageEntity]]
    parse_mode: Optional[str]
    reply_markup: Optional[Union[InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply]]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class MessageEditor:
    """
    Класс для упрощённой отправки и редактирования сообщений.
    Сохраняет необходимую дальнейшего редактирования информацию при отправке.

    Решение о том необходимо ли редактировать медиа производится следующим образом:
    - Медиа представлено как url или file_id и url или file_id изменились
    - Медиа представлено как InputFile и filename изменился
    - Или параметр force_edit_media установлен на True
    """

    def __init__(self, *, always_edit_media: bool = False):
        super().__init__()

        self._always_edit_media = always_edit_media

        self._media_type: Optional[Literal[
            'nm',  # No media
            'lp',  # LinkPreview
            'p',  # Photo
            'a',  # Animation
            'v',  # Video
            'd',  # Document
            'au'  # Audio
        ]] = None
        self._media_id: Optional[str] = None  # url, file_id or filename
        self._is_input_file: Optional[bool] = None  # If true, media_id is filename

    def _set_media_id(self, media: Union[InputFile, str]) -> None:
        if isinstance(media, InputFile):
            self._media_id = media.filename
            self._is_input_file = True
        elif isinstance(media, str):
            self._media_id = media
            self._is_input_file = False
        else:
            raise TypeError('Invalid media')

    def _is_media_needs_to_be_edited(self, media: Optional[IMediaType]):
        if self._media_type != media.media_type:
            return True

        is_input_file = isinstance(media.media, InputFile)

        if is_input_file != self._is_input_file:
            return True

        if is_input_file:
            return media.media.filename != self._media_id

        return media.media != self._media_id

    async def send(
            self,
            message: MeMessage,
            chat_id: Union[int, str],
            message_thread_id: Optional[int] = None,
            disable_notification: Optional[bool] = None,
            protect_content: Optional[bool] = None,
            reply_parameters: Optional[ReplyParameters] = None
    ) -> Message:
        parameters = {
            'chat_id': chat_id,
            'message_thread_id': message_thread_id,
            'disable_notification': disable_notification,
            'protect_content': protect_content,
            'reply_parameters': reply_parameters
        }

        if message.media is None:
            self._media_type = 'nm'

            return await bot.send_message(
                link_preview_options=LinkPreviewOptions(
                    is_disabled=True
                ),

                text=message.text,
                entities=message.entities,
                parse_mode=message.parse_mode,
                reply_markup=message.reply_markup,
                **parameters
            )

        if isinstance(message.media, MeLinkPreview):
            self._media_type = 'lp'

            # noinspection DuplicatedCode
            return await bot.send_message(
                link_preview_options=LinkPreviewOptions(
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

        if isinstance(message.media, MePhoto):
            self._media_type = 'p'
            self._set_media_id(message.media.photo)

            return await bot.send_photo(
                photo=message.media.photo,
                has_spoiler=message.media.has_spoiler,

                caption=message.text,
                caption_entities=message.entities,
                parse_mode=message.parse_mode,
                reply_markup=message.reply_markup,
                **parameters
            )

        if isinstance(message.media, MeAnimation):
            self._media_type = 'a'
            self._set_media_id(message.media.animation)

            return await bot.send_animation(
                animation=message.media.animation,
                duration=message.media.duration,
                width=message.media.width,
                height=message.media.height,
                thumb=message.media.thumbnail,
                has_spoiler=message.media.has_spoiler,

                caption=message.text,
                caption_entities=message.entities,
                parse_mode=message.parse_mode,
                reply_markup=message.reply_markup,
                **parameters
            )

        if isinstance(message.media, MeVideo):
            self._media_type = 'v'
            self._set_media_id(message.media.video)

            return await bot.send_video(
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

        if isinstance(message.media, MeDocument):
            self._media_type = 'd'
            self._set_media_id(message.media.document)

            return await bot.send_document(
                document=message.media.document,
                thumbnail=message.media.thumbnail,
                disable_content_type_detection=message.media.disable_content_type_detection,

                caption=message.text,
                caption_entities=message.entities,
                parse_mode=message.parse_mode,
                reply_markup=message.reply_markup,
                **parameters
            )

        if isinstance(message.media, MeAudio):
            self._media_type = 'au'
            self._set_media_id(message.media.audio)

            return await bot.send_audio(
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

        raise NotImplementedError('Unknown media type')

    async def edit(
            self,
            message: MeMessage,
            chat_id: Optional[Union[int, str]] = None,
            message_id: Optional[int] = None,
            inline_message_id: Optional[str] = None,
            force_edit_media: bool = False
    ) -> Union[Message, bool]:
        parameters = {
            'chat_id': chat_id,
            'message_id': message_id,
            'inline_message_id': inline_message_id
        }

        if self._media_type in ('nm', 'lp') and message.media is None:
            self._media_type = 'nm'

            return await bot.edit_message_text(
                link_preview_options=LinkPreviewOptions(
                    is_disabled=False
                ),

                text=message.text,
                entities=message.entities,
                parse_mode=message.parse_mode,
                reply_markup=message.reply_markup,
                **parameters
            )

        if self._media_type in ('nm', 'lp') and isinstance(message.media, MeLinkPreview):
            self._media_type = 'lp'

            # noinspection DuplicatedCode
            return await bot.edit_message_text(
                link_preview_options=LinkPreviewOptions(
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
        if self._media_type in ('nm', 'lp'):
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

        if isinstance(message.media, MePhoto):
            self._media_type = 'p'

            return await bot.edit_message_media(
                media=InputMediaPhoto(
                    media=message.media.photo,
                    has_spoiler=message.media.has_spoiler,
                    caption=message.text,
                    caption_entities=message.entities,
                    parse_mode=message.parse_mode
                ),
                reply_markup=message.reply_markup,
                **parameters
            )

        if isinstance(message.media, MeAnimation):
            self._media_type = 'a'

            return await bot.edit_message_media(
                media=InputMediaAnimation(
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

        if isinstance(message.media, MeVideo):
            self._media_type = 'v'

            return await bot.edit_message_media(
                media=InputMediaVideo(
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

        if isinstance(message.media, MeDocument):
            self._media_type = 'd'

            return await bot.edit_message_media(
                media=InputMediaDocument(
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

        if isinstance(message.media, MeAudio):
            self._media_type = 'au'

            return await bot.edit_message_media(
                media=InputMediaAudio(
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
