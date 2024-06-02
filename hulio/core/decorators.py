import inspect
import typing as t

from pydantic import BaseModel

from .attribute import set_attribute
from .classes.component import Component


class ContextInfo(BaseModel):
    alias: str


def context(f, *, alias: str = None):
    """ Decorated method will become a property and will be included
        in a context on render """

    def decorate(fn):
        prop = property(fn)

        set_attribute(prop, 'action', ContextInfo(
            alias=(
                alias if alias is not None
                else inspect.unwrap(fn).__name__
            )
        ))

        return prop

    if f is None:
        return decorate
    return decorate(f)


class ButtonInfo(BaseModel):
    alias: str
    callback_data_alias: str
    filters: t.Iterable[t.Callable]


def button(f, *, alias: str = None, callback_data_alias: str = None, filters: t.Iterable[t.Callable] = None):
    """ Decorated method will be registered as an inline button handler """

    def decorate(fn):
        set_attribute(fn, 'action', ButtonInfo(
            alias=(
                alias if alias is not None
                else inspect.unwrap(fn).__name__
            ),
            callback_data_alias=(
                callback_data_alias if callback_data_alias is not None
                else alias if alias is not None
                else inspect.unwrap(fn).__name__
            ),
            filters=filters if filters is not None else []
        ))

        return fn

    if f is None:
        return decorate
    return decorate(f)


class TextInfo(BaseModel):
    filters: t.Iterable[t.Callable]


def text(f, *, filters: t.Iterable[t.Callable] = None):
    """ Decorated method will be registered as a message handler """

    def decorate(fn):
        set_attribute(fn, 'action', TextInfo(
            filters=filters if filters is not None else []
        ))

        return fn

    if f is None:
        return decorate
    return decorate(f)


class ChildClosedInfo(BaseModel):
    component: t.Optional[str]


def child_closed(f, *, component: t.Union[type[Component], str] = None):
    """ Decorated method will be registered as handler for
        stacked component's .close() method """

    def decorate(fn):
        set_attribute(fn, 'action', ChildClosedInfo(
            component=(
                component.get_component_id() if issubclass(component, Component)
                else component
            )
        ))

        return fn

    if f is None:
        return decorate
    return decorate(f)
