"""Configures standard logging to go through loguru."""
import logging

from loguru import logger


class InterceptHandler(logging.Handler):
    """Logging interceptor that passes log messages into loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        """Converts standard log records into loguru logs."""
        level: int | str
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # find the caller of the log message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            if not frame.f_back:
                break

            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def set_loguru_intercept() -> None:
    """Adds the intercept handler to the standard logging config."""
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
