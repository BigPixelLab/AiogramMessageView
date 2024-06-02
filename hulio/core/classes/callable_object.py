import asyncio
import contextvars
import inspect
import typing as t
from dataclasses import dataclass, field
from functools import partial


@dataclass
class CallableObject:
    callback: t.Callable[..., t.Any]

    arguments: set[str] = field(init=False)
    has_kwargs: bool = field(init=False)
    is_awaitable: bool = field(init=False)

    def __post_init__(self) -> None:
        callback = inspect.unwrap(self.callback)
        self.is_awaitable = inspect.isawaitable(callback) or inspect.iscoroutinefunction(callback)

        spec = inspect.getfullargspec(callback)
        self.arguments = {*spec.args, *spec.kwonlyargs}
        self.has_kwargs = spec.varkw is not None

    def _filter_kwargs(self, kwargs: dict[str, t.Any]) -> dict[str, t.Any]:
        if self.has_kwargs:
            return kwargs

        return {k: kwargs[k] for k in self.arguments if k in kwargs}

    async def call(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        wrapped = partial(self.callback, *args, **self._filter_kwargs(kwargs))

        if self.is_awaitable:
            return await wrapped()

        loop = asyncio.get_event_loop()
        context = contextvars.copy_context()
        wrapped = partial(context.run, wrapped)

        return await loop.run_in_executor(None, wrapped)
