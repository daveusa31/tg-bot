import logging


LOGGER = logging.getLogger("migrate")
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.INFO)
