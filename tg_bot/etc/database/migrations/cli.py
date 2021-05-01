""" CLI integration. """
import os
import re
import sys
from playhouse.db_url import connect

from .compat import string_types


VERBOSE = ['WARNING', 'INFO', 'DEBUG', 'NOTSET']
CLEAN_RE = re.compile(r'\s+$', re.M)


def get_router(directory, database, schema=None, verbose=0):
    """Load and initialize a router."""
    from .router import Router
    from .logger import LOGGER
    from .compat import exec_in

    logging_level = VERBOSE[verbose]
    config = {}
    ignore = None
    try:
        with open(os.path.join(directory, "conf.py")) as cfg:
            exec_in(cfg.read(), config, config)
            database = config.get('DATABASE', database)
            ignore = config.get('IGNORE', ignore)
            schema = config.get('SCHEMA', schema)
            logging_level = config.get('LOGGING_LEVEL', logging_level).upper()
    except IOError:
        pass

    if isinstance(database, string_types):
        database = connect(database)

    LOGGER.setLevel(logging_level)

    try:
        return Router(database, directory, ignore=ignore, schema=schema)
    except RuntimeError as exc:
        LOGGER.error(exc)

