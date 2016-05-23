import logging

logger = logging.getLogger(__name__)

logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s : %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


def set_identity_string(identifier):
    global ch
    formatter = logging.Formatter(identifier+"%(asctime)s : %(message)s")
    ch.setFormatter(formatter)