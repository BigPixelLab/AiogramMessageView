"""
Использование модуля::

    >>> import template
    >>> template.render('path_to_template.xml', {}, syntax=...)

"""
from ._template import (

    TemplateModuleError,
    RegistrationError,
    HandlerError,
    ParsingError,
    ParsingCoroutineError,
    SpecifierError,
    ConvertingError,

    get_default_syntax,
    set_default_syntax,
    get_global_context,
    set_global_context,
    render_string,
    render,
)
