import sys
import os
import you_get
from PySide2.QtWidgets import QApplication, QLabel
from windows import MainWindow
from utils.logger import get_logger

logger = get_logger()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        you_get.main()
    else:
        logger.info(f'process start at: {os.getpid()}')
        app = QApplication(sys.argv)
        main_window = MainWindow()
        main_window.show()
        sys.exit(app.exec_())
