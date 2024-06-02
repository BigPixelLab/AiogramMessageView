from contextvars import ContextVar

current_component: ContextVar = ContextVar('current_component')
current_bot: ContextVar = ContextVar('current_bot')
