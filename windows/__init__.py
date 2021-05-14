# -*- coding: UTF-8 -*-
from enum import Flag
import sys
import json
from io import StringIO
from PySide2 import QtGui
from PySide2.QtWidgets import QAbstractItemView, QHeaderView, QMainWindow, QStyle, QStyleOptionButton, QTableWidgetItem
from PySide2.QtCore import QRect, QThread, Qt, Signal, Slot
from windows.ui import mainwindow, optionwindow, aboutwindow, parsedwindow
from utils.logger import get_logger
from you_get.common import any_download

logger = get_logger()


class RedirectedStdout:
    def __init__(self):
        self._stdout = None
        self._string_io = None

    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._string_io = StringIO()
        return self

    def __exit__(self, type, value, traceback):
        sys.stdout = self._stdout

    def __str__(self):
        return self._string_io.getvalue()


class ParseThread(QThread):
    finished = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        with RedirectedStdout() as out:
            any_download(self.parent().linkLineEdit.text(), json_output=True)
        self.finished.emit(str(out))


class OptionWindow(QMainWindow, optionwindow.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)


class AboutWindow(QMainWindow, aboutwindow.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)


class QCheckableHeaderView(QHeaderView):
    # https://stackoverflow.com/questions/9744975/pyside-pyqt4-adding-a-checkbox-to-qtablewidget-horizontal-column-header
    isOn = False

    checkBoxClicked = Signal(bool)

    def __init__(self, orientation, parent=None):
        QHeaderView.__init__(self, orientation, parent)

    def paintSection(self, painter, rect, logicalIndex):
        painter.save()
        QHeaderView.paintSection(self, painter, rect, logicalIndex)
        painter.restore()

        if logicalIndex == 0:
            option = QStyleOptionButton()
            option.rect = QRect(3, 7, 10, 10)
            if self.isOn:
                option.state = QStyle.State_On
            else:
                option.state = QStyle.State_Off
            self.style().drawControl(QStyle.CE_CheckBox, option, painter)

    def updateCheckBox(self):
        self.isOn = not self.isOn
        self.updateSection(0)
        return self.isOn


class ParsedWindow(QMainWindow, parsedwindow.Ui_MainWindow):
    def __init__(self, parent=None, is_playlist=False):
        super().__init__(parent)
        self.setupUi(self)
        self.parse_thread = ParseThread(self)
        
        self.table_titles = ['标题', '站点', '清晰度', '格式', '大小']
        self.format_index = 3
        if is_playlist:
            self.table_titles = ['标题', '列表标题', '站点', '清晰度', '格式', '大小']
            self.format_index = 4
        
        self.parsedTableWidget.setColumnCount(len(self.table_titles))
        for index, table_title in enumerate(self.table_titles):
            self.parsedTableWidget.setHorizontalHeaderItem(index, QTableWidgetItem(table_title))

        # parsedTableWidget
        self.parsedCheckableHeaderView = QCheckableHeaderView(Qt.Horizontal, self)
        self.parsedCheckableHeaderView.setSectionsClickable(True)
        self.parsedCheckableHeaderView.sectionClicked.connect(self.call_update_section)
        self.parsedTableWidget.setHorizontalHeader(self.parsedCheckableHeaderView)
        self.parsedTableWidget.verticalHeader().setHidden(True) # 隐藏默认的行号
        self.parsedTableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) # 设置自适应宽度
        self.parsedTableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)    # 禁用表格编辑
        self.parsedTableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)   # 设置item选中时选择整行
        self.parsedTableWidget.itemChanged.connect(self.call_update_checkbox)
        self.sort_asc = False   # 排序
        self.global_checkbox = Qt.Unchecked # 全局checkbox选择器

        self.parse_thread.finished.connect(self.call_update_table)

        self.current_format = 0
        self.format_list = []
        self.formatComboBox.currentIndexChanged.connect(self.call_filter_by_format)

        self.reparsePushButton.clicked.connect(self.call_reparse)
        self.downloadSelectedPushButton.clicked.connect(self.call_download)

        self.download_task_list = []

    def _parse(self, url):
        self.statusBar().showMessage(f'开始解析: {url}')
        self.parse_thread.start()

    def start_parse(self, url):
        self.linkLineEdit.setText(url)
        logger.info(f'start parse: {url}')
        self._parse(url)
        
    def call_reparse(self):
        url = self.linkLineEdit.text()
        self.parsedTableWidget.clearContents()
        self.parsedTableWidget.setRowCount(0)
        self.formatComboBox.clear()
        self.formatComboBox.addItem('格式')
        logger.info(f'start reparse: {url}')
        self._parse(url)

    def call_filter_table(self):
        rows = self.parsedTableWidget.rowCount()
        if self.formatComboBox.currentIndex() == 0:
            for row in range(rows):
                self.parsedTableWidget.setRowHidden(row, False)
                self.parsedTableWidget.item(row, 0).setCheckState(self.global_checkbox)
        else:
            format = self.formatComboBox.itemText(self.formatComboBox.currentIndex())
            for row in range(rows):
                if self.parsedTableWidget.item(row, self.format_index).text() == format:
                    self.parsedTableWidget.setRowHidden(row, False)
                    self.parsedTableWidget.item(row, 0).setCheckState(self.global_checkbox)
                else:
                    item = self.parsedTableWidget.item(row, 0)
                    if item.checkState() == Qt.Checked:
                        item.setCheckState(Qt.Unchecked)
                    self.parsedTableWidget.setRowHidden(row, True)

    def call_filter_by_format(self):
        # 切换过滤条件时，强制将所有checkbox值为unchecked
        self.global_checkbox = Qt.Unchecked
        self.parsedCheckableHeaderView.isOn = False
        self.parsedCheckableHeaderView.updateSection(0)

        self.call_filter_table()

    def call_update_table(self, data):
        data = json.loads(data)
        rows = len(data.get('streams'))
        streams_keys = list(data.get('streams').keys())
        streams_values = list(data.get('streams').values())

        self.format_list += streams_keys
        self.format_list.sort()
        self.formatComboBox.addItems(set(self.format_list))

        for row in range(rows):
            row = self.parsedTableWidget.rowCount()
            self.parsedTableWidget.insertRow(row)
            for col, title in enumerate(self.table_titles):
                if title == '标题':
                    item = QTableWidgetItem(data.get('title'))
                    item.setCheckState(Qt.Unchecked)
                    item.setToolTip(data.get('title'))
                elif title == '站点':
                    item = QTableWidgetItem(data.get('site'))
                    item.setTextAlignment(Qt.AlignCenter)
                elif title == '清晰度':
                    item = QTableWidgetItem(streams_values[row].get('quality'))
                elif title == '格式':
                    item = QTableWidgetItem(streams_keys[row])
                elif title == '大小':
                    item = QTableWidgetItem()
                    # 通过setData方法解决排序错误问题
                    item.setData(Qt.EditRole, streams_values[row].get('size'))
                elif title == '列表标题':
                     item = QTableWidgetItem(streams_keys[row])
                self.parsedTableWidget.setItem(row, col, item)

        self.parsedTableWidget.horizontalHeader().setSortIndicatorShown(True)
        self.parsedTableWidget.sortByColumn(self.format_index + 1, Qt.DescendingOrder)
        self.statusBar().showMessage(f'解析完成')
        logger.info(f'parse finished: {self.linkLineEdit.text()}')

    def call_update_checkbox(self, item):
        check_state = item.checkState()
        if check_state == Qt.Checked:
            stream_id = item.row()
            if stream_id not in self.download_task_list:
                self.download_task_list.append(stream_id)
            show_rows = 0

            # 当显示行数与被选中行数一致时，将全局checkbox置为checked
            for row in range(self.parsedTableWidget.rowCount()):
                if self.parsedTableWidget.isRowHidden(row) is False:
                    show_rows += 1
            if len(self.download_task_list) == show_rows:
                if self.global_checkbox == Qt.Unchecked:
                    self.update_global_checkbox()

        elif check_state == Qt.Unchecked:
            stream_id = item.row()
            if stream_id in self.download_task_list:
                self.download_task_list.remove(stream_id)
            
            # 任意显示行checkbox状态为unchecked时，将全局checkbox置为unchecked
            if self.global_checkbox == Qt.Checked:
                self.update_global_checkbox()
        self.statusBar().showMessage(f'已选中 {len(self.download_task_list)} 个')

    def update_global_checkbox(self):
        status = self.parsedCheckableHeaderView.updateCheckBox()
        self.global_checkbox = Qt.Checked if status else Qt.Unchecked

    def call_update_section(self, logicalIndex):
        if logicalIndex == 4:
            # 通过 大小 列进行排序，默认desc
            self.parsedTableWidget.horizontalHeader().setSortIndicatorShown(True)
            if self.sort_asc == False:
                self.parsedTableWidget.sortByColumn(logicalIndex, Qt.AscendingOrder)
            else:
                self.parsedTableWidget.sortByColumn(logicalIndex, Qt.DescendingOrder)
            self.sort_asc = not self.sort_asc
        else:
            # 第一列表头被点击时，切换全局checkbox状态
            if logicalIndex == 0:
                self.update_global_checkbox()
                self.call_filter_table()
            self.parsedTableWidget.horizontalHeader().setSortIndicatorShown(False)

    def call_download(self):
        logger.info(f'got {len(self.download_task_list)} download task: {self.download_task_list}')


class MainWindow(QMainWindow, mainwindow.Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.option_window = OptionWindow(self)
        self.about_window = AboutWindow(self)

        self.actionOptions.triggered.connect(self.render_option_window)
        self.actionAbout.triggered.connect(self.render_about_window)
        self.parsePushButton.clicked.connect(self.render_parsed_window)

        self.actionQuit.triggered.connect(self.close)
        self.actionMinsize.triggered.connect(self.showMinimized)
        self.statusBar.showMessage('启动成功')


    def render_option_window(self):
        self.statusBar.showMessage('option_window called.')
        self.option_window.show()

    def render_about_window(self):
        self.about_window.show()

    def render_parsed_window(self):
        link = self.linkLineEdit.text()
        if not link:
            self.statusBar.showMessage('目标链接不能为空')
        else:
            parsed_window = ParsedWindow(self)
            parsed_window.show()
            parsed_window.start_parse(link.strip())