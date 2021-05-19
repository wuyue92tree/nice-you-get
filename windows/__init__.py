# -*- coding: UTF-8 -*-
from re import I
import sys
import os
import json
from io import StringIO
from PySide2 import QtCore
from PySide2.QtGui import QDesktopServices, QStandardItemModel, QStandardItem
from PySide2.QtWidgets import QAbstractItemView, QFileDialog, QHeaderView, QMainWindow, QStyle, QStyleOptionButton
from PySide2.QtCore import QRect, QRegExp, QThread, QUrl, Qt, Signal, Slot, QSortFilterProxyModel
from windows.ui import mainwindow, parsedwindow, downloadwindow
from utils.logger import get_logger
from utils.config import config
from utils.patch import any_download

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
            any_download(self.parent().linkValueLabel.text(), json_output=True)
        self.finished.emit(str(out))


class DownloadThread(QThread):
    processUpdated = Signal(dict)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def run(self):
        save_path = config.load().get('save_path')
        merge = False if config.load().get('merge') == 0 else True
        insecure = False if config.load().get('insecure') == 0 else True
        caption = False if config.load().get('caption') == 0 else True
        if not save_path:
            os.mkdir(save_path)
        any_download(
            self.parent().linkValueLabel.text(), 
            output_dir=save_path,
            merge=merge,
            insecure=insecure,
            caption=caption, 
            stream_id=self.parent().formatValueLabel.text(),
            qt_signer=self.processUpdated
        )
        self.finished.emit(True)


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


class MultiSortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        QSortFilterProxyModel.__init__(self, *args, **kwargs)
        self.filters = {}

    def setFilterByColumn(self, regex, column):
        self.filters[column] = regex
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        for key, regex in self.filters.items():
            ix = self.sourceModel().index(source_row, key, source_parent)
            if ix.isValid():
                text = self.sourceModel().data(ix)
                if not regex.exactMatch(text):
                    return False
        return True


class ParsedWindow(QMainWindow, parsedwindow.Ui_MainWindow):
    def __init__(self, parent=None, is_playlist=False):
        super().__init__(parent)
        self.setupUi(self)
        self.parse_thread = ParseThread(self)
        
        self.table_titles = ['标题', '站点', '清晰度', '媒体格式', '格式', '大小']
        self.format_index = 3
        self.size_index = 5
        if is_playlist:
            self.table_titles = ['标题', '列表标题', '站点', '清晰度','媒体格式', '格式', '大小']
            self.format_index = 4
            self.size_index = 6

        # parsedTableView
        self.model = QStandardItemModel(self)
        self.model.setHorizontalHeaderLabels(self.table_titles)
        
        self.proxy = MultiSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)

        self.parsedCheckableHeaderView = QCheckableHeaderView(Qt.Horizontal, self)
        self.parsedCheckableHeaderView.setSectionsClickable(True)
        self.parsedCheckableHeaderView.sectionClicked.connect(self.on_parsedCheckableHeaderView_sectionClicked)
        self.parsedTableView.setHorizontalHeader(self.parsedCheckableHeaderView)
        self.parsedTableView.verticalHeader().setHidden(True) # 隐藏默认的行号
        self.parsedTableView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) # 设置自适应宽度
        self.parsedTableView.setEditTriggers(QAbstractItemView.NoEditTriggers)    # 禁用表格编辑
        self.parsedTableView.setSelectionBehavior(QAbstractItemView.SelectRows)   # 设置item选中时选择整行
        self.parsedTableView.setModel(self.proxy)
        self.model.itemChanged.connect(self.on_model_itemChanged)
        self.sort_asc = False   # 排序
        self.global_checkbox = Qt.Unchecked # 全局checkbox选择器

        self.parse_thread.finished.connect(self.on_parse_thread_finished)

        self.format_list = []
        self.formatComboBox.currentIndexChanged.connect(self.on_formatComboBox_currentIndexChanged)
        self.container_list = []
        self.containerComboBox.currentIndexChanged.connect(self.on_containerComboBox_currentIndexChanged)

        self.reparsePushButton.clicked.connect(self.on_reparsePushButton_clicked)
        self.downloadSelectedPushButton.clicked.connect(self.on_downloadSelectedPushButton_clicked)

        self.download_task_list = []

    def _parse(self, url):
        self.statusBar().showMessage(f'开始解析: {url}')
        self.parse_thread.start()

    def start_parse(self, url):
        self.linkValueLabel.setText(url)
        logger.info(f'start parse: {url}')
        self._parse(url)
        
    def on_reparsePushButton_clicked(self):
        url = self.linkValueLabel.text()
        self.model.removeRows( 0, self.model.rowCount())

        self.formatComboBox.clear()
        self.formatComboBox.addItem('媒体格式')

        self.containerComboBox.clear()
        self.containerComboBox.addItem('格式')

        logger.info(f'start reparse: {url}')
        self._parse(url)

    def set_global_checkbox2unchecked(self):
        # 切换过滤条件时，强制将所有checkbox值为unchecked
        self.global_checkbox = Qt.Unchecked
        self.parsedCheckableHeaderView.isOn = False
        self.parsedCheckableHeaderView.updateSection(0)
        for row in range(self.model.rowCount()):
            self.model.item(row, 0).setCheckState(Qt.Unchecked)

    def on_formatComboBox_currentIndexChanged(self, index):
        self.set_global_checkbox2unchecked()
        filter = QRegExp(
            self.formatComboBox.itemText(index) if index != 0 else '.*',  
            QtCore.Qt.CaseInsensitive, QtCore.QRegExp.RegExp
        )
        self.proxy.setFilterByColumn(filter, self.format_index)
        
    def on_containerComboBox_currentIndexChanged(self, index):
        self.set_global_checkbox2unchecked()
        filter = QRegExp(
            self.containerComboBox.itemText(index) if index != 0 else '.*',  
            QtCore.Qt.CaseInsensitive, QtCore.QRegExp.RegExp
        )
        self.proxy.setFilterByColumn(filter, self.format_index+1)

    def on_parse_thread_finished(self, data):
        data = json.loads(data)
        rows = len(data.get('streams'))
        streams_keys = list(data.get('streams').keys())
        streams_values = list(data.get('streams').values())

        self.format_list += streams_keys
        self.format_list.sort()

        # 添加一个隐藏列，用于存储最初的行号
        self.model.setHorizontalHeaderItem(len(self.table_titles), QStandardItem('origin_row_id'))
        self.parsedTableView.setColumnHidden(len(self.table_titles), True)

        for row in range(rows):
            for col, title in enumerate(self.table_titles):
                if title == '标题':
                    item = QStandardItem(data.get('title'))
                    item.setCheckState(Qt.Unchecked)
                    item.setCheckable(True)
                    item.setToolTip(data.get('title'))
                elif title == '站点':
                    item = QStandardItem(data.get('site'))
                    item.setTextAlignment(Qt.AlignCenter)
                elif title == '清晰度':
                    item = QStandardItem(streams_values[row].get('quality'))
                    item.setTextAlignment(Qt.AlignCenter)
                elif title == '媒体格式':
                    item = QStandardItem(streams_keys[row])
                    item.setTextAlignment(Qt.AlignCenter)
                elif title == '格式':
                    item = QStandardItem(streams_values[row].get('container'))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.container_list.append(item.text())
                elif title == '大小':
                    item = QStandardItem(str(streams_values[row].get('size')))
                    # 通过setData方法解决排序错误问题 (使用tableWidget时存在此问题)
                    # item.setData(Qt.EditRole, streams_values[row].get('size'))
                elif title == '列表标题':
                    item = QStandardItem(streams_keys[row])
                self.model.setItem(row, col, item)
            
            # 行号赋值
            self.model.setItem(row, len(self.table_titles), QStandardItem(str(row)))

        self.formatComboBox.addItems(set(self.format_list))
        self.containerComboBox.addItems(set(self.container_list))

        self.parsedTableView.horizontalHeader().setSortIndicatorShown(True)
        self.parsedTableView.sortByColumn(self.size_index, Qt.DescendingOrder)
        self.statusBar().showMessage(f'解析完成')
        logger.info(f'parse finished: {self.linkValueLabel.text()}')

    def on_model_itemChanged(self, item):
        check_state = item.checkState()
        row = item.row()
        
        if check_state == Qt.Checked:
            if row not in self.download_task_list:
                self.download_task_list.append(row)

            # 当显示行数与被选中行数一致时，将全局checkbox置为checked
            if len(self.download_task_list) == self.proxy.rowCount():
                if self.global_checkbox == Qt.Unchecked:
                    self.update_global_checkbox()

        elif check_state == Qt.Unchecked:
            if row in self.download_task_list:
                self.download_task_list.remove(row)
            
            # 任意显示行checkbox状态为unchecked时，将全局checkbox置为unchecked
            if self.global_checkbox == Qt.Checked:
                self.update_global_checkbox()
        self.statusBar().showMessage(f'已选中 {len(self.download_task_list)} 个')

    def update_global_checkbox(self):
        status = self.parsedCheckableHeaderView.updateCheckBox()
        self.global_checkbox = Qt.Checked if status else Qt.Unchecked

    def on_parsedCheckableHeaderView_sectionClicked(self, logicalIndex):
        if logicalIndex == self.size_index:
            # 通过 大小 列进行排序，默认desc
            self.parsedTableView.horizontalHeader().setSortIndicatorShown(True)
            if self.sort_asc == False:
                self.parsedTableView.sortByColumn(logicalIndex, Qt.AscendingOrder)
            else:
                self.parsedTableView.sortByColumn(logicalIndex, Qt.DescendingOrder)
            self.sort_asc = not self.sort_asc
        else:
            self.parsedTableView.horizontalHeader().setSortIndicatorShown(False)
            # 第一列表头被点击时，切换全局checkbox状态
            if logicalIndex == 0:
                self.update_global_checkbox()
                for row in range(self.model.rowCount()):
                            self.model.item(row, 0).setCheckState(Qt.Unchecked)

                for row in range(self.proxy.rowCount()):
                    origin_row_id = int(self.proxy.data(self.proxy.index(row, len(self.table_titles))))
                    self.model.item(origin_row_id, 0).setCheckState(self.global_checkbox)

    def on_downloadSelectedPushButton_clicked(self):
        logger.info(f'got {len(self.download_task_list)} download task: {self.download_task_list}')
        if len(self.download_task_list) > 1:
            self.statusBar().showMessage('暂不支持多个媒体同时下载')
            return 
        for row in self.download_task_list:
            download_window = DownloadWindow(self, row)
            download_window.show()


class DownloadWindow(QMainWindow, downloadwindow.Ui_MainWindow):
    def __init__(self, parent, row):
        super(DownloadWindow, self).__init__(parent)
        self.setupUi(self)
        self.titleValueLabel.setText(
            self.parent().model.item(row, 0).text()
        )
        self.linkValueLabel.setText(
            self.parent().linkValueLabel.text()
        )
        self.qualityValueLabel.setText(
            self.parent().model.item(row, self.parent().format_index-1).text()
        )
        self.formatValueLabel.setText(
            self.parent().model.item(row, self.parent().format_index).text()
        )
        self.containerValueLabel.setText(
            self.parent().model.item(row, self.parent().format_index+1).text()
        )

        self.download_thread = DownloadThread(self)
        self.statusBar().showMessage('开始下载')
        self.download_thread.start()
        self.download_thread.processUpdated.connect(self.on_download_thread_processUpdated)
        self.download_thread.finished.connect(self.on_download_thread_finished)

    def on_download_thread_processUpdated(self, process):
        # logger.debug(f'download process update {json.dumps(process)}')
        self.downloadProgressBar.setValue(process.get('percent'))
        if self.downloadProgressBar.value() == 100:
            self.speedLabel.setText('done')
            return
        self.speedLabel.setText(process.get('speed').strip())

    def on_download_thread_finished(self):
        self.statusBar().showMessage('下载完成')


class MainWindow(QMainWindow, mainwindow.Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        self.init_config()
        self.mediaSavePushButton.clicked.connect(self.change_save_path)
        self.mediaPathPushButton.clicked.connect(self.open_save_path_folder)

        self.insecureCheckBox.stateChanged.connect(self.update_insecure_config)
        self.downlaodCaptionheckBox.stateChanged.connect(self.update_download_caption_config)
        self.mergeCheckBox.stateChanged.connect(self.update_merge_config)

        self.actionAbout.triggered.connect(self.render_about_window)
        self.parsePushButton.clicked.connect(self.render_parsed_window)

        self.actionQuit.triggered.connect(self.close)
        self.actionMinsize.triggered.connect(self.showMinimized)
        self.statusBar.showMessage('启动成功')

    def init_config(self):
        self.mediaPathValueLabel.setText(config.load().get('save_path'))
        self.insecureCheckBox.setCheckState(Qt.CheckState(config.load().get('insecure')))
        self.downlaodCaptionheckBox.setCheckState(Qt.CheckState(config.load().get('caption')))
        self.mergeCheckBox.setCheckState(Qt.CheckState(config.load().get('merge')))

    def change_save_path(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹", "/")
        logger.info(f'the new save_path {folder}')
        config.save(save_path=folder)
        self.mediaPathValueLabel.setText(folder)
        logger.info(f'save_path change to {folder}')

    def open_save_path_folder(self):
        if sys.platform == 'darwin':
            os.system(f'open {self.mediaPathValueLabel.text()}')
        else:
            os.startfile(self.mediaPathValueLabel.text())

    def update_insecure_config(self, states):
        config.save(insecure=states)
        logger.info(f'you-get insecure config update to {states}')

    def update_download_caption_config(self, states):
        config.save(caption=states)
        logger.info(f'you-get caption config update to {states}')

    def update_merge_config(self, states):
        config.save(merge=states)
        logger.info(f'you-get merge config update to {states}')

    def render_about_window(self):
        QDesktopServices.openUrl(QUrl('https://github.com/wuyue92tree/nice-you-get'))

    def render_parsed_window(self):
        link = self.linkLineEdit.text()
        if not link:
            self.statusBar.showMessage('目标链接不能为空')
        else:
            parsed_window = ParsedWindow(self)
            parsed_window.show()
            parsed_window.start_parse(link.strip())