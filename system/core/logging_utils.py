from __future__ import annotations
import logging
from contextlib import contextmanager
from typing import Callable, TypeVar, Any, Optional, Iterable

T = TypeVar("T")

def setup_basic_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    fmt = "[%(levelname)s] %(asctime)s %(name)s — %(message)s"
    logging.basicConfig(level=level, format=fmt)

def log_exception(logger: logging.Logger, level: int, msg: str, exc: BaseException) -> None:
    logger.log(level, f"{msg}: {exc.__class__.__name__}: {exc}", exc_info=True)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

def log_calls(logger: logging.Logger) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def deco(fn: Callable[..., T]) -> Callable[..., T]:
        def wrapped(*args: Any, **kwargs: Any) -> T:
            logger.debug("→ %s args=%r kwargs=%r", fn.__name__, args, kwargs)
            try:
                res = fn(*args, **kwargs)
                logger.debug("← %s ok=%r", fn.__name__, res)
                return res
            except Exception as e:  # specific logging while preserving original behavior
                log_exception(logger, logging.WARNING, f"Unhandled in {fn.__name__}", e)
                raise
        return wrapped
    return deco

@contextmanager
def capture_errors(logger: logging.Logger, context: str, re_raise: bool = True):
    try:
        yield
    except Exception as e:
        log_exception(logger, logging.WARNING, f"Error in {context}", e)
        if re_raise:
            raise