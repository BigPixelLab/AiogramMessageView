import typing as t
import uuid

import pydantic as pd

import classes.message_editor as me


InlineButtonAction = ...
TextInputAction = ...
KeyLock = ...


REG_VIEWS_TABLE = {}


class BaseView(pd.BaseModel):
    record_id: t.Optional[uuid.UUID] = pd.Field(init_var=False, default=None)
    # message: me.MeMessage = pd.Field(init_var=False, default_factory=me.MessageEditor)

    # Global view identifier
    _view_id: t.ClassVar[str]

    # Defines if new view objects will be tracked when sent
    _is_tracked_by_default: t.ClassVar[bool]

    def __init_subclass__(cls, alias: str = None, tracked: bool = None, **kwargs):
        if alias is None:
            alias = cls.__name__

        if alias in REG_VIEWS_TABLE:
            raise ValueError  # View with given id is already registered

        cls._view_id = alias
        REG_VIEWS_TABLE[cls._view_id] = cls

        if tracked is not None:
            cls._is_tracked_by_default = tracked
        else:
            cls._is_tracked_by_default = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # View can only be restored if it is present in the database,
        #   and it is present in the database only if record_id is set.
        #   So on the first initialization record_id will be None, so
        #   we call __created__ method, then view is sent and if it is
        #   tracked record_id is set
        if self.record_id is None:
            self.__created__()

    def __created__(self):
        """ Overridable. Called first time a view is created (not restored from the database) """
        pass

    def save(self):
        """ Saves tracked view's state to the database """
        pass


class SupportsInlineButtons(BaseView):
    _inline_button_actions: t.ClassVar[dict[str, InlineButtonAction]]

    def __init_subclass__(cls, tracked: bool = None, **kwargs):
        super().__init_subclass__(tracked=tracked, **kwargs)

        cls._inline_button_actions = {}
        _track = False

        for field in cls.__dict__.values():
            action = getattr(field, '__action__', None)

            if isinstance(action, InlineButtonAction):
                cls._inline_button_actions[action.action_id] = action
                _track = True

        if tracked is None:
            # We want views with actions to be tracked, plus other
            # classes could change this attribute
            cls._is_tracked_by_default = cls._is_tracked_by_default or _track
        else:
            cls._is_tracked_by_default = tracked

    async def call_inline_button_action(self, action_id: str, args: dict):
        action = self._inline_button_actions[action_id]

        async with KeyLock(self.record_id):
            await action.call(self, **args)
            self.save()


class SupportsTextInput(BaseView):
    _text_input_actions: t.ClassVar[list[TextInputAction]]

    # Defines if new view objects will be focused when sent
    _is_focused_by_default: t.ClassVar[bool]

    def __init_subclass__(cls, tracked: bool = None, focused: bool = None, **kwargs):
        super().__init_subclass__(tracked=tracked, **kwargs)

        cls._text_input_actions = []
        _focus = False
        _track = False

        for field in cls.__dict__.values():
            action = getattr(field, '__action__', None)

            if isinstance(action, TextInputAction):
                cls._text_input_actions.append(action)
                _focus = True
                _track = True

        if focused is None:
            cls._is_focused_by_default = _focus
        else:
            cls._is_focused_by_default = focused

        if tracked is None:
            # We want views with actions to be tracked, plus other
            # classes could change this attribute
            cls._is_tracked_by_default = cls._is_tracked_by_default or _track
        else:
            cls._is_tracked_by_default = tracked

    async def call_text_input_action(self, args: dict):
        for action in self._text_input_actions:
            async with KeyLock(self.record_id):
                await action.call(self, **args)
        self.save()


class View(SupportsInlineButtons):
    pass
