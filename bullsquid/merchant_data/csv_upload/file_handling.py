"""
Utility functions for handling files.
"""
import codecs
import csv
from typing import BinaryIO, Generator, Type, TypeVar

import charset_normalizer
from loguru import logger

from bullsquid.merchant_data.models import BaseModel


def detect_encoding(buf: BinaryIO) -> str:
    """
    Use charset-normalizer to detect the encoding of the given IO stream.
    Returns utf-8-sig for utf-8 files with a leading byte-order mark.
    """
    if (charset := charset_normalizer.from_fp(buf).best()) is None:
        raise ValueError("failed charset detection")

    if charset.encoding == "utf_8" and charset.bom:
        encoding = "utf-8-sig"
    else:
        encoding = charset.encoding

    buf.seek(0)

    return encoding


TModel = TypeVar("TModel", bound=BaseModel)  # pylint: disable=invalid-name


def csv_model_reader(
    buf: BinaryIO, *, row_model: Type[TModel]
) -> Generator[TModel, None, None]:
    """
    Yields Pydantic models from a CSV file.
    """
    encoding = detect_encoding(buf)
    logger.info(
        f"yielding {row_model.__name__} records from file with encoding {encoding}"
    )
    stream = codecs.iterdecode(buf, encoding)
    fieldnames = list(row_model.__fields__.keys())
    reader = csv.reader(stream)
    next(reader)  # skip header row  # pylint: disable=stop-iteration-return

    yield from (row_model.parse_obj(dict(zip(fieldnames, record))) for record in reader)
