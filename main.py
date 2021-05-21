import sys
import io

# fix pyinstaller --windowed issue case by you_get.
# you_get will modify sys.stdout.buffer, but when packaged, stdout bin 
# setup to NullWriter at `pyiboot01_bootstrap.py`
# issue just like: 
# https://github.com/pyinstaller/pyinstaller/issues/3503
# https://github.com/pyinstaller/pyinstaller/issues/1883
if "NullWriter" in str(type(sys.stdout)):
    sys.stdout.buffer = io.BytesIO()


import os
from PySide2.QtWidgets import QApplication
from windows import MainWindow
from utils.logger import get_logger

logger = get_logger()


if __name__ == '__main__':
    logger.info(f'process start at: {os.getpid()}')
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
