import logging


def log(*args):
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logging.info(' '.join(map(str, args)))
