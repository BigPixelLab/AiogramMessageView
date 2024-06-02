import inspect
import typing as t


def set_attribute(f, key, value):
    """ Sets functions attributes, that can later be retrieved.
        Works well with decorators that use __wrapped__ """

    fn = inspect.unwrap(f)

    try:
        if key in fn.__attributes__:
            raise ValueError(f'Attribute {key} already set for function {fn.__name__}')

        fn.__attributes__[key] = value
    except AttributeError:
        fn.__attributes__ = {key: value}


def get_attribute(f, key):
    """ Get functions attribute, stored in __attributes__ dictionary.
        Works well with decorators that use __wrapped__ """

    fn = inspect.unwrap(f)

    try:
        return fn.__attributes__[key]
    except (AttributeError, KeyError):
        return None


def get_attributes(f):
    """ Get functions attributes, stored in __attributes__ dictionary.
        Works well with decorators that use __wrapped__.
        Returns shallow copy of __attributes__ """

    fn = inspect.unwrap(f)

    try:
        return fn.__attributes__.copy()
    except AttributeError:
        return None


def attribute(key: str, value: t.Any):
    """ Sets functions attributes, that can later be retrieved.
        Works well with decorators that use __wrapped__ """

    def decorate(fn):
        set_attribute(fn, key, value)
        return fn

    return decorate


__all__ = (
    'set_attribute',
    'get_attribute',
    'get_attributes',
    'attribute'
)
