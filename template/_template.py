import dataclasses
import functools
from pathlib import Path
from typing import Callable, Generator, Optional, Type, Any, Union, Iterable, Generic, TypeVar
from xml.dom import minidom
from xml.dom.minidom import Element, Document

T = TypeVar('T')


class ReadOnlyDict(dict):
    def __readonly__(self, *args, **kwargs):
        raise RuntimeError("Cannot modify ReadOnlyDict")

    __setitem__ = __readonly__
    __delitem__ = __readonly__
    pop = __readonly__
    popitem = __readonly__
    clear = __readonly__
    update = __readonly__
    setdefault = __readonly__
    del __readonly__


class MutableVariable(Generic[T]):
    __slots__ = ('_value',)

    def __init__(self, initial: T):
        self._value: T = initial

    @property
    def value(self) -> T:
        return self._value

    @value.setter
    def value(self, value: T):
        self._value = value


class TemplateModuleError(Exception):
    pass


class RegistrationError(TemplateModuleError):
    pass


class HandlerError(TemplateModuleError):
    pass


class ParsingError(TemplateModuleError):
    pass


class ParsingCoroutineError(ParsingError):
    pass


class SpecifierError(ParsingError):
    pass


class ConvertingError(SpecifierError):
    pass


class ConvertBy:
    class _Convert:
        __slots__ = ('convert',)

        def __init__(self, func):
            self.convert: Callable = func

    def __class_getitem__(cls, function: Callable) -> _Convert:
        return cls._Convert(function)

    def __iter__(self):
        raise NotImplementedError


def str2bool(value: str) -> bool:
    """ Преобразует строку в boolean """
    try:
        return {'True': True, 'False': False}[value]
    except KeyError:
        raise ConvertingError(f'Unable to convert "{value}" to bool, try using "True" or "False"')


def str2list(item_conv, sep=',') -> Union[Callable[[str], list], list]:
    """ Возвращает converter, преобразующий строку в список. Или, если передана
        строка - преобразует её в список """

    # if item_conv is a string then we're already converting.
    # Helpful then using like this:
    #   `ConvertBy[str2list]`
    if isinstance(item_conv, str):
        return list(map(str.strip, item_conv.split(sep)))

    # if you need to preserve spaces around items, you
    # can use function as follows:
    #   `ConvertBy[str2list(None)]`
    if item_conv is None:
        return lambda x: x.split(sep)

    # any function that gets str and returns any can
    # be set as a converter:
    #   `ConvertBy[str2list(int)]`
    return lambda x: list(map(item_conv, x.split(sep)))


def converting_specifier(value, _, target_type) -> Any:
    """
    Конвертирует переданную строку в указанный тип. Использует таблицу,
    для сопоставления типа с конвертером. Можно указать сторонний конвертер
    передав в качестве target_type значение ConvertBy[converter], где
    converter - конвертирующая функция.

    Пример::

        >>> converting_specifier('5', None, int)
        5

        >>> converting_specifier('1,2,3', None, ConvertBy[str2list(int)])
        [1, 2, 3]

    :param value: Значение для конвертации.
    :param _:
    :param target_type: Тип, к которому необходимо привести значение.
    :return: Преобразованное значение.
    """

    # noinspection PyProtectedMember
    if isinstance(target_type, ConvertBy._Convert):
        return target_type.convert(value)

    try:
        converter = converters[target_type]
    except KeyError:
        raise SpecifierError(f'There is no converter for "{target_type}" (type={type(target_type)})')

    return converter(value)


def f_converting_specifier(value, context, target_type) -> Any:
    """
    Конвертирует переданную строку в указанный тип, предварительно форматируя
    используя контекст. Использует таблицу, для сопоставления типа с
    конвертером. Можно указать сторонний конвертер передав в качестве
    target_type значение ConvertBy[converter], где converter - конвертирующая функция.

    Пример::

        >>> f_converting_specifier('1,{val},3', {'val': '2'}, ConvertBy[str2list(int)])
        [1, 2, 3]

        >>> f_converting_specifier('1,{val},3', {'val': 'Hi'}, ConvertBy[str2list(int)])
        TypeError

    :param value: Значение для конвертации.
    :param context: Контекст, используемый для форматирования исходной строки.
    :param target_type: Тип, к которому необходимо привести значение.
    :return: Преобразованное значение.
    """

    return converting_specifier(value.format_map(context), context, target_type)


def context_var_specifier(value, context, _) -> Any:
    """
    Возвращает значение переменной контекста с указанным именем. Преобразование
    типов при этом не производится.

    Пример::

        >>> context_var_specifier('val2', {'val1': 1, 'val2': 'Hello!', 'val3': False}, None)
        Hello!

    :param value: Имя переменной контекста для поиска.
    :param context: Контекст для поиска.
    :param _:
    :return: Значение переменной с указанным именем в контексте.
    """
    try:
        return context[value]
    except KeyError:
        raise SpecifierError(f'Context variable "{value}" expected, but not provided')


def exec_python_specifier(value, context, target_type) -> Any:
    """
    Выполняет значение, как python код и возвращает результат. При использовании
    данной функции результат не преобразуется к ожаемому типу автоматически.
    Из окружения кода можно напрямую получить доступ к значениям переменных контекста,
    а также добавляются переменные "__target__" для доступа к ожидаемому обработчиком
    типу, и "__context__" для доступа к контексту как к словарю.

    Пример::

        >>> exec_python_specifier('[1, 2, 3]', {}, list)
        [1, 2, 3]

        >>> exec_python_specifier('[1, 2, 3]', {}, bool)
        [1, 2, 3]

        >>> exec_python_specifier('val[0]', {'val': [1, 2, 3]}, ...)
        1

        >>> exec_python_specifier('__context__["val"]', {'val': [1, 2, 3]}, ...)
        [1, 2, 3]

        >>> exec_python_specifier('__target__(val)', {'val': '123'}, int)
        123

    :param value: Код для выполнения.
    :param context: Контекст, который будет передан в код.
    :param target_type: Тип, который будет передан в код.
    :return: Значение переменной с указанным именем в контексте.
    """
    return eval(value, {}, {**context, '__target__': target_type, '__context__': context})


converters = {
    bool: str2bool,
    float: float,
    int: int,
    str: str,
}

specifiers = {
    '': f_converting_specifier,
    'nf': converting_specifier,
    'cv': context_var_specifier,
    'py': exec_python_specifier,
}

StopParsing = object()
""" Объект, используемый для указания parser-у о завершении обработки """


class ParsingScope:
    DISPLAY_ATTRIBUTE_IF = 'if'
    DISPLAY_ATTRIBUTE_ELSE_IF = 'else-if'
    DISPLAY_ATTRIBUTE_ELSE = 'else'
    DUPLICATE_ATTRIBUTE = 'for'
    DUPLICATE_SEPARATOR = ' in '
    """ Атрибуты использующиеся для указания условного отображения элемента и его дублирования"""

    REMAINING_ARGUMENT = '__rem'
    """ Аргумент в который будут переданы все указанные в теге, но не объявленные в обработчике атрибуты """

    TAG_ARGUMENT = 'tag'

    @dataclasses.dataclass
    class Handler:
        function: Callable
        annotations: dict[str, Type]
        defaults: dict[str, Any]
        takes_remaining: bool

    def __init__(self, parsing_function: Callable[[], Generator]):
        self.parsing_function = parsing_function
        self.text_handler: Optional[Callable] = None
        self.handlers: dict[str, ParsingScope.Handler] = {}

    # Parsing -------------------------------------------------------

    def __arguments__(
            self,
            annotations: dict[str, Type],
            defaults: dict[str, Any],
            takes_remaining: bool,
            attributes: dict[str, str],
            context: ReadOnlyDict
    ) -> dict[str, Any]:
        """ По переданным аттрибутам тега и ожидаемым аргументам собирает
            значения для передачи в обработчик """

        # Отделение спецификаторов от имён аргументов
        arguments = {}
        for attribute, value in attributes.items():
            try:
                attribute, spec = attribute.split('.', maxsplit=1)
            except ValueError:
                spec = ''

            try:
                converter = specifiers[spec]
            except KeyError:
                raise ParsingError(f'No such specifier as "{spec}" is registered')

            arguments[attribute] = value, converter

        # Проверка соответствия между переданными аргументами и ожидаемыми
        provided = set(arguments)
        annotated = set(annotations)
        mandatory = annotated - set(defaults)

        if unprovided := mandatory - provided:
            raise ParsingError(f'Arguments {unprovided} were expected, but not provided')
        if not takes_remaining and (unexpected := provided - annotated):
            raise ParsingError(f'Got unexpected arguments {unexpected}')

        # Формирование аргументов
        args = {}
        for arg in provided.intersection(annotated):
            value, convert = arguments[arg]
            args[arg] = convert(value, context, annotations[arg])
        for arg in annotated - provided:
            args[arg] = defaults[arg]

        if not takes_remaining:
            return args

        remaining = {}
        for arg in provided - annotated:
            value, convert = arguments[arg]
            remaining[arg] = convert(value, context, str)

        args[self.REMAINING_ARGUMENT] = remaining

        return args

    def __display__(self, attributes: dict[str, str], context: ReadOnlyDict,
                    cond_status: MutableVariable[Optional[bool]]) -> bool:
        """ Вызывается на каждом элементе, чтобы определить должен
            ли он быть отображён """
        cond_attr_present = (
            (self.DISPLAY_ATTRIBUTE_IF in attributes)
            + (self.DISPLAY_ATTRIBUTE_ELSE_IF in attributes)
            + (self.DISPLAY_ATTRIBUTE_ELSE in attributes)
        )

        if cond_attr_present > 1:
            raise ParsingError('There must be only one of "if", "else-if" or "else" in a single tag')

        if cond_attr_present == 0:
            return True

        # "if" attribute

        cond = attributes.pop(self.DISPLAY_ATTRIBUTE_IF, None)

        if cond is not None:
            cond_status.value = bool(exec_python_specifier(cond, context, bool))
            return cond_status.value

        # "else-if" attribute

        cond = attributes.pop(self.DISPLAY_ATTRIBUTE_ELSE_IF, None)

        if cond is not None:
            if cond_status.value is None:
                raise ParsingError('Tag with "else-if" attribute must come somewhere after '
                                   'a tag with "if" attribute')

            cond_status.value = not cond_status.value \
                and bool(exec_python_specifier(cond, context, bool))

            return cond_status.value

        # "else" attribute

        cond = attributes.pop(self.DISPLAY_ATTRIBUTE_ELSE, None)

        if cond is not None:
            if cond_status.value is None:
                raise ParsingError('Tag with "else" attribute must come somewhere after '
                                   'a tag with "if" or "else-if" attribute')

            if len(cond) != 0:
                raise ParsingError('Content of the "else" attribute must be empty')

            result = not cond_status.value
            cond_status.value = None
            return result

        # Should be unreachable, unless there is an error in this code
        raise

    def __duplicate__(self, attributes: dict[str, str], context: ReadOnlyDict) -> Iterable[ReadOnlyDict]:
        """ Вызывается на каждом элементе, чтобы определить сколько
            раз он должен быть отображён """
        try:
            value = attributes.pop(self.DUPLICATE_ATTRIBUTE)
        except KeyError:
            # Таким образом при отсутствии необходимости в
            # дублировании элемента контекст не копируется
            yield context
            return

        try:
            cvs, source_cv = value.split(self.DUPLICATE_SEPARATOR, maxsplit=1)
        except ValueError:
            raise ParsingError('Value of the "for" argument must contain "in" in it')

        source = exec_python_specifier(source_cv, context, None)

        # 'a, b , c' -> ['a', 'b', 'c']
        cvs = list(map(lambda x: x.strip(), cvs.split(',')))

        # <tag for="a,b in [(val1, val2), (val3, val4), ...]"/>
        if len(cvs) > 1:
            yield from (ReadOnlyDict(**context, **{cv: item for cv, item in zip(cvs, value)})
                        for value in source)
            return

        # <tag for="a in [val1, val2, ...]"/>
        cv, = cvs
        yield from (ReadOnlyDict(**context, **{cv: value}) for value in source)

    def parse(self, element: Element, context: ReadOnlyDict) -> Any:
        parser = self.parsing_function()

        try:
            next(parser)
        except StopIteration:
            raise ParsingCoroutineError('Parser returned StopIteration after initialization')

        cond_status = MutableVariable(None)
        for element in element.childNodes:
            self.process(parser, element, context, cond_status)

        try:
            return parser.send(StopParsing)
        except StopIteration:
            raise ParsingCoroutineError('Parser returned StopIteration after receiving StopParsing')

    def process(self, parser: Generator, element: Element, context: ReadOnlyDict,
                cond_status: MutableVariable[Optional[bool]]):

        if element.nodeType == Element.TEXT_NODE and self.text_handler:
            tag = Tag(self, parser, element, context)
            token = self.text_handler(tag)
            self.send(parser, token)
            return

        if element.nodeType != Element.ELEMENT_NODE:
            return

        # Предполагается, что словарь будет изменяться методами
        # __display__ и __duplicate__, конкретно - будут удаляться
        # атрибуты 'if' и 'for', если они есть
        attributes = dict(element.attributes.items())

        if not self.__display__(attributes, context, cond_status):
            return

        try:
            handler = self.handlers[element.tagName]
        except KeyError:
            raise ParsingError(f'Got unexpected tag "{element.tagName}"')

        for child_context in self.__duplicate__(attributes, context):
            tag = Tag(self, parser, element, child_context)
            arguments = self.__arguments__(
                handler.annotations,
                handler.defaults,
                handler.takes_remaining,
                attributes,
                child_context
            )
            token = handler.function(tag, **arguments)

            # Обработчик не вернул значения
            if token is None:
                return

            self.send(parser, token)

    def send(self, parser: Generator, token: Any):
        if token is StopParsing:
            raise ParsingError('Attempt to return "StopParsing" from the handler')

        try:
            parser.send(token)
        except StopIteration:
            raise ParsingCoroutineError(f'Parser returned StopIteration after receiving '
                                        f'"{token}" (type={type(token)})')

    # Регистрация обработчиков --------------------------------------

    def _register(self, func, name: Union[list[str] | str] = None, override: bool = False,
                  annotations: dict = None, defaults: dict = None):

        # Получаем имя тега
        if name is None:
            name = getattr(func, '__name__', None)
        if name is None:
            raise RegistrationError('Cannot extract tag name, provide name explicitly')

        if isinstance(name, str):
            name = [name]

        _used_names = set(name).intersection(self.handlers.keys())
        if isinstance(name, list) and _used_names and not override:
            raise RegistrationError(f'Handlers with names {_used_names} already registered')

        # Получаем аннотации типов
        if not annotations:
            annotations = getattr(func, '__annotations__', None)
        if annotations is None:
            raise RegistrationError(f'({name}) Cannot extract annotations, provide annotations explicitly')

        annotations = annotations.copy()
        takes_remaining = self.REMAINING_ARGUMENT in annotations

        annotations.pop(self.REMAINING_ARGUMENT, None)
        annotations.pop(self.TAG_ARGUMENT, None)
        annotations.pop('return', None)

        # Получаем значения по-умолчанию
        if not defaults:
            defaults = getattr(func, '__kwdefaults__', None)
        if not defaults and getattr(func, '__defaults__', None):
            raise RegistrationError('Cannot properly extract defaults. Try making arguments kw-only, '
                                    'ex.: def handler(tag: Tag, *, arg1, arg2=5)')
        defaults = defaults or {}

        if unexpected := set(defaults.keys()) - set(annotations.keys()):
            raise RegistrationError(f'You cannot provide defaults to unlisted arguments: {unexpected}')

        handler = self.Handler(func, annotations, defaults, takes_remaining)

        for alias in name:
            self.handlers[alias] = handler

        return func

    def register(self, func=None, /, name: Union[list[str] | str] = None, override: bool = False,
                 annotations: dict = None, defaults: dict = None) -> Callable:
        """
        Регистрирует обработчик тега. Данный обработчик будет вызываться для элементов с указанным
        именем тега

        :param func: Обработчик тега, ответственен за преобразование Element-ов в принимаемые
            parser-ом данные
        :param name: Имя тега как оно будет встречаться в шаблоне. Если не указано, будет
            автоматически извлечено из имени функции
        :param override: Если перезаписывается существующий обработчик, это должно быть явно указано
            с помощью данного аргумента
        :param annotations: Аргументы, используемые тегом, с указанием их типов. Если не указано,
            будет автоматически извлечено из __annotations__
        :param defaults: Значения по умолчанию для аргументов обработчика. Если не указано,
            будет автоматически извлечено из __kwdefaults__
        """

        if func is None:
            return functools.partial(self._register, name, override, annotations, defaults)
        return self._register(func, name, override, annotations, defaults)

    def register_text(self, func=None):
        """
        Регистрирует текстовый обработчик. Данный обработчик будет вызываться для каждого xml элемента
        с типом TEXT_ELEMENT
        """

        if self.text_handler:
            raise RegistrationError('There is already a text handler')

        self.text_handler = func
        return func


def register_text(parsers: Iterable[ParsingScope]) -> Callable:
    """
    Регистрирует текстовый обработчик. Данный обработчик будет вызываться для каждого xml элемента
    с типом TEXT_ELEMENT

    :param parsers: Области в которых необходимо зарегистрировать обработчик
    """
    def decorator(func):
        for parser in parsers:
            parser.register_text(func)
        return func
    return decorator


def register(scopes: Iterable[ParsingScope], name: Union[list[str] | str] = None, override: bool = False,
             annotations: dict = None, defaults: dict = None) -> Callable:
    """
    Регистрирует обработчик тега. Данный обработчик будет вызываться для элементов с указанным
    именем тега

    :param scopes: Области в которых необходимо зарегистрировать обработчик
    :param name: Имя тега как оно будет встречаться в шаблоне. Если не указано, будет
        автоматически извлечено из имени функции
    :param override: Если перезаписывается существующий обработчик, это должно быть явно указано
        с помощью данного аргумента
    :param annotations: Аргументы, используемые тегом, с указанием их типов. Если не указано,
        будет автоматически извлечено из __annotations__
    :param defaults: Значения по умолчанию для аргументов обработчика. Если не указано,
        будет автоматически извлечено из __kwdefaults__
    """
    def decorator(func):
        for scope in scopes:
            scope.register(
                func,
                name=name,
                override=override,
                annotations=annotations,
                defaults=defaults
            )
        return func
    return decorator


class Tag:
    def __init__(
            self,
            scope: ParsingScope,
            parser: Generator,
            element: Element,
            context: ReadOnlyDict
    ):
        self._scope = scope
        self._parser = parser
        self._element = element
        self._context = context

    @property
    def element(self):
        return self._element

    @property
    def context(self):
        return self._context

    def process(self, element: Element, context: Union[ReadOnlyDict, dict] = None,
                cond_status: MutableVariable[Optional[bool]] = None):
        """
        Обрабатывает элемент как если бы он был частью шаблона.

        Рекомендуется использовать только если элемент действительно
        должен пройти через весь процесс parsing-а. В большинстве
        случаев возможно ограничиться `Tag.send()`.

        Например::

            @register([EXAMPLE])
            def wow(tag: Tag):
                elem = minidom.parseString('<p> WOW! </p>')
                tag.process(elem, tag.context)

            <example>
                <wow/>
            </example>

        Интерпретируется как::

            <example>
                <p> WOW! </p>
            </example>

        Также позволяет использовать специальные аттрибуты::

            @register([EXAMPLE])
            def wow(tag: Tag):
                elem = minidom.parseString('<p for="i in range(5)"> WOW #{i}! </p>')
                tag.process(elem, tag.context)

            <example>
                <p> WOW #0! </p>
                <p> WOW #1! </p>
                <p> WOW #2! </p>
                <p> WOW #3! </p>
                <p> WOW #4! </p>
            </example>

        Если в элементе используются (или могут использоваться) условные атрибуты,
        такие как "if", "else-if" или "else" - в функцию следует также передавать
        cond_status, который будет передавать состояние условий между тегами::

            @register([EXAMPLE])
            def wow(tag: Tag):
                elem = minidom.parseString('''
                    <section>
                        <p if="a"> WOW #1! </p>
                        <p else-if="b"> WOW #2! </p>
                        <p else=""> WOW #3! </p>
                    </section>
                ''')

                cond_status = MutableVariable(None)
                for element in elem.childNodes:
                    tag.process(element, {'a': False, 'b': True}, cond_status)

            <example>
                <section>
                    <p> WOW #2! </p>
                </section>
            </example>

        """
        if context and not isinstance(context, ReadOnlyDict):
            context = ReadOnlyDict(context)
        if context is None:
            context = self._context

        if cond_status is None:
            cond_status = MutableVariable(None)

        # Обычно ParsingScope.process не возвращает ничего при вызове,
        # но может начать при наследовании
        return self._scope.process(self._parser, element, context, cond_status)

    def send(self, token: Any):
        """
        Отправляет токен в функцию-parser. Аналогично возврату значения
        из handler-а, за исключением передачи None, т.к. возврат None
        из обработчика сигнализирует, что значение быть передано не должно,
        в то время как его передача через `Tag.send` будет явным указанием
        того, что parser должен получить None.

        Например::

            def example() -> Generator[str, str, None]:
                message = 'Life is going on'

                # Принимаем токены пока не кончатся
                while (token := (yield)) is not StopParsing:
                    message += token

                yield message

            EXAMPLE = ParsingScope(example)

            @register([EXAMPLE])
            def hi(tag: Tag):
                tag.send(' and on')
                tag.send(' and on')
                tag.send(' and on...')

            <example>
                <hi/>
            </example>

        Даст в результате::

            'Life is going on and on and on and on...'

        Данный метод стоит использовать, если из handler-а необходимо
        вернуть несколько значений или None, в противном случае лучше использовать
        `return` для улучшения читаемости кода

        """

        # Обычно ParsingScope.process не возвращает ничего при вызове,
        # но может начать при наследовании
        return self._scope.send(self._parser, token)


_default_syntax: Optional[ParsingScope] = None
_global_context: dict = {}


def set_default_syntax(syntax: ParsingScope):
    """ Устанавливает синтаксис глобально """
    global _default_syntax
    _default_syntax = syntax


def get_default_syntax() -> ParsingScope:
    """ Возвращает установленный глобально синтаксис """
    return _default_syntax


def set_global_context(context: dict):
    """ Устанавливает контекст глобально """
    global _global_context
    _global_context = context


def get_global_context() -> dict:
    """ Возвращает установленный глобально контекст """
    return _global_context


def render_document(document: Document, context: dict, path: str = None, syntax: ParsingScope = None):
    global _default_syntax
    global _global_context

    syntax = syntax or _default_syntax
    if syntax is None:
        raise ValueError('No default syntax is set, so it must be provided manually')

    _context = _global_context.copy()
    if path:
        path = Path(path)
        _context.update(__dir__=path.parent, __file__=path)
    _context.update(context)

    # noinspection PyTypeChecker
    return syntax.parse(document, ReadOnlyDict(_context))


def render_string(string: str, context: dict, syntax: ParsingScope = None):
    return render_document(
        minidom.parseString(string),
        context,
        syntax=syntax
    )


def render(path: str, context: dict, syntax: ParsingScope = None):
    return render_document(
        minidom.parse(path),
        context,
        path=path,
        syntax=syntax
    )


__all__ = (
    'ReadOnlyDict',
    'MutableVariable',
    'TemplateModuleError',
    'RegistrationError',
    'HandlerError',
    'ParsingError',
    'ParsingCoroutineError',
    'SpecifierError',
    'ConvertingError',
    'ConvertBy',
    'str2bool',
    'str2list',
    'converting_specifier',
    'f_converting_specifier',
    'context_var_specifier',
    'exec_python_specifier',
    'converters',
    'specifiers',
    'StopParsing',
    'ParsingScope',
    'register_text',
    'register',
    'Tag',
    'set_default_syntax',
    'set_global_context',
    'get_default_syntax',
    'get_global_context',
    'render_document',
    'render_string',
    'render',
)
