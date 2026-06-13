"""
Message dataclass: code + text (supports static strings and format strings).
"""
from typing import Callable


class Message:
    def __init__(self, code: str, msg: str | Callable[..., str]):
        self.msg_code = code
        self._msg = msg

    def text(self, *args, **kwargs) -> str:
        if callable(self._msg):
            return self._msg(*args, **kwargs)
        return str(self._msg).format(*args, **kwargs) if (args or kwargs) else str(self._msg)
