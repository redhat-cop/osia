"""Module implements utilitary functions shared by download
package"""
import logging
from pathlib import Path
from typing import Callable
from tempfile import NamedTemporaryFile

import requests


def get_data(tar_url: str,
             target: str,
             processor: Callable[[NamedTemporaryFile, str], Path]) -> str:
    """Function downloads file via http and runs it through
    processor function for extraction"""
    result = None
    logging.debug('[get_data] Starting the download of %s', tar_url)
    req = requests.get(tar_url, stream=True, allow_redirects=True)
    buf = NamedTemporaryFile()
    for block in req.iter_content(chunk_size=4096):
        buf.write(block)
    buf.flush()
    logging.debug('[get_data] Download finished, starting extraction')
    result = processor(buf, target)
    buf.close()

    logging.debug('[get_data] File extracted to %s', result.as_posix())
    return result.as_posix()
