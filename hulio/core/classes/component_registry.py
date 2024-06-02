"""
ComponentRegistry - Реестр компонентов.

Реестры компонентов имеют очень узкую среду применения. При создании компонента
он регистрируется в реестре, откуда его потом можно получить.
Реестры можно использовать как способ группировки компонентов, однако поскольку
все компоненты в любом случае регистрируются в глобальном реестре, все они
должны иметь уникальный component_id. Также это обусловлено тем, что когда
приходит callback data, реестр там нигде не указывается, и если бы реестры могли
содержать компоненты с одинаковыми ИД - возникла бы неопределённость
"""


class ComponentLazyProxy:
    """ Прокси класс, создающий объект компонента при вызове """

    def __init__(self, registry: 'ComponentRegistry', component_id: str, default: None = ...):
        self._origin_component_id = component_id
        self._registry = registry
        self._raise = default is not None

    @property
    def __origin__(self):
        return self._registry.get(self._origin_component_id, self._raise)

    def __getattr__(self, item):
        return getattr(self.__origin__, item)

    def __call__(self, **kwargs):
        return self.__origin__(**kwargs)


class ComponentRegistry:
    """ Реестр компонентов """

    def __init__(self, debug_name: str = None):
        self._debug_name = debug_name
        self._components = {}

    def register(self, component_id: str, component):
        """ Регистрирует компонент в системе """
        if component_id in self._components:
            message = f'Component with id "{component_id}" is already registered'
            if self._debug_name is not None:
                message += f' in "{self._debug_name}"'
            raise ValueError(message)

        self._components[component_id] = component

    def get_lazy(self, component_id: str, default: None = ...):
        """ Возвращает прокси, создающий объект зарегистрированного компонента при вызове """
        return ComponentLazyProxy(self, component_id, default)

    def get(self, component_id: str, default: None = ...):
        """ Возвращает зарегистрированный компонент """
        try:
            return self._components[component_id]
        except KeyError:
            if default is None:
                return None
            raise
