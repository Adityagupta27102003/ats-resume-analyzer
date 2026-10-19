import logging
import sys
from typing import Callable, Optional, Tuple, TypeVar

# Log to stdout only — containers (HF Spaces / Docker) collect stdout, and the
# app directory may not be writable at runtime.
logger = logging.getLogger('ats_resume_scorer')
logger.setLevel(logging.INFO)

if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)


class ATSBaseError(Exception):
    """Base class for errors whose `user_message` is safe to show to the client."""
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.user_message = user_message or message

class FileValidationError(ATSBaseError):
    pass

class FileParsingError(ATSBaseError):
    pass

class TextExtractionError(ATSBaseError):
    pass


def log_error(error: Exception, context: Optional[str] = None) -> None:
    logger.error(f"Error in {context or 'unknown'}: {error}")

def log_warning(message: str, context: Optional[str] = None) -> None:
    logger.warning(f"{context}: {message}" if context else message)

def log_info(message: str, context: Optional[str] = None) -> None:
    logger.info(f"{context}: {message}" if context else message)


T = TypeVar('T')

def with_fallback(
    primary_func: Callable[..., T],
    fallback_func: Callable[..., T],
    *args,
    log_fallback: bool = True,
    **kwargs
) -> Tuple[T, bool]:
    """Run primary_func; on any exception run fallback_func. Returns (result, used_fallback)."""
    try:
        return primary_func(*args, **kwargs), False
    except Exception as primary_error:
        if log_fallback:
            log_warning(f"Primary method failed, trying fallback: {primary_error}")
        return fallback_func(*args, **kwargs), True
