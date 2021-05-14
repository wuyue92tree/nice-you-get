import os
import logging
import logging.handlers
import datetime
from conf.settings import HOME_DIR


def get_logger():
    logger = logging.getLogger('nice_you_get')
    logger.setLevel(logging.DEBUG)
    console_hander = logging.StreamHandler()
    console_hander.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    console_hander.setLevel(logging.INFO)

    rf_handler = logging.handlers.TimedRotatingFileHandler(os.path.join(HOME_DIR, 'all.log'), when='midnight', interval=1, backupCount=10, atTime=datetime.time(0, 0, 0, 0))
    rf_handler.setFormatter(logging.Formatter("%(asctime)s %(filename)s %(funcName)s %(processName)s %(threadName)s [line:%(lineno)d] %(levelname)s: %(message)s"))
    rf_handler.setLevel(logging.DEBUG)

    f_handler = logging.FileHandler(os.path.join(HOME_DIR, 'error.log'))
    f_handler.setFormatter(logging.Formatter("%(asctime)s %(filename)s %(funcName)s %(processName)s %(threadName)s [line:%(lineno)d] %(levelname)s: %(message)s"))
    f_handler.setLevel(logging.ERROR)

    if not logger.handlers:
        logger.addHandler(console_hander)
        logger.addHandler(rf_handler)
        logger.addHandler(f_handler)
    return logger
