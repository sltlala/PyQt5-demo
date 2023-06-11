# -*- coding: UTF-8 -*-

import datetime
from functools import wraps
import json
import math
import os
import re
import sqlite3
import srt
import subprocess
import sys
import time
from traceback import format_exception
import urllib.parse
import webbrowser

import keyboard
import threading
import platform
import signal

import pymediainfo
import io
from shutil import rmtree, move
try:
    os.chdir(os.path.dirname(__file__))
except:
    print('更改工作目录失败，关系不大，不用管它')

import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtSql import *
from PyQt5.QtWidgets import *
import requests


# from PyQt5.QtWidgets import QListWidget, QWidget, QApplication, QFileDialog, QMainWindow, QDialog, QLabel, QLineEdit, QTextEdit, QPlainTextEdit, QTabWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout, QPushButton, QCheckBox, QSplitter
# from PyQt5.QtGui import QCloseEvent
# from PyQt5.QtCore import Qt

# print('开始运行')
dbname = './database.db'  # 存储预设的数据库名字
presetTableName = 'commandPreset'  # 存储预设的表单名字
ossTableName = 'oss'
apiTableName = 'api'
preferenceTableName = 'preference'
styleFile = './style.css'  # 样式表的路径
finalCommand = ''
version = 'V1.6.10'



############# 主窗口和托盘 ################

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._update_checker = None
        self.initGui()
        self.loadStyleSheet()
        self.status = self.statusBar()
        self._start_checker()


        # self.setWindowState(Qt.WindowMaximized)
        # sys.stdout = Stream(newText=self.onUpdateText)

    def initGui(self):
        # 定义中心控件为多 tab 页面
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # 定义多个不同功能的 tab
        self.ffmpegMainTab = FFmpegMainTab()  # 主要功能的 tab
        self.ffmpegSplitVideoTab = FFmpegSplitVideoTab()  # 分割视频 tab
        # self.ffmpegCutVideoTab = FFmpegCutVideoTab()  # 剪切视频的 tab
        self.ffmpegConcatTab = FFmpegConcatTab()  # 合并视频的 tab
        # self.ffmpegBurnCaptionTab = FFmpegBurnCaptionTab()  # 烧字幕的 tab

         # 创建一个可以发送信号的对象，用于告知其他界面 api列表已经更新


        # self.consoleTab = ConsoleTab() # 新的控制台输出 tab
        self.helpTab = HelpTab()  # 帮助
        # self.aboutTab = AboutTab()  # 关于

        # 将不同功能的 tab 添加到主 tabWidget
        self.tabs.addTab(self.ffmpegMainTab, self.tr('FFmpeg'))

        self.tabs.addTab(self.ffmpegSplitVideoTab, self.tr('分割视频'))
        # self.tabs.addTab(self.ffmpegCutVideoTab, '截取片段')
        self.tabs.addTab(self.ffmpegConcatTab, self.tr('合并片段'))
        # self.downloadTabScroll = QScrollArea()
        # self.downloadTabScroll.setWidget(self.downloadVidwoTab)
        # self.downloadVidwoTab.setObjectName('widget')
        # self.downloadVidwoTab.setStyleSheet("QWidget#widget{background-color:transparent;}")
        # self.downloadTabScroll.setStyleSheet("QScrollArea{background-color:transparent;}")
        # self.tabs.addTab(self.downloadTabScroll, '下载视频')
        self.tabs.addTab(self.downloadVidwoTab, self.tr('下载视频'))
        # self.tabs.addTab(self.ffmpegBurnCaptionTab, '嵌入字幕')
        self.tabs.addTab(self.ffmpegAutoEditTab, self.tr('自动剪辑'))
        self.tabs.addTab(self.ffmpegAutoSrtTab, self.tr('自动字幕'))
        self.tabs.addTab(self.capsWriterTab, self.tr('语音输入'))
        self.tabs.addTab(self.ConfigTab, self.tr('设置'))
        # self.tabs.addTab(self.consoleTab, '控制台')
        self.tabs.addTab(self.helpTab, self.tr('帮助'))
        # self.tabs.addTab(self.aboutTab, '关于')

        self.adjustSize()
        if platfm == 'Darwin':
            self.setWindowIcon(QIcon('misc/icon.icns'))
        else:
            self.setWindowIcon(QIcon('misc/icon.ico'))
        self.setWindowTitle('Quick Cut')

        # self.setWindowFlag(Qt.WindowStaysOnTopHint) # 始终在前台

        self.show()

    def loadStyleSheet(self):
        global styleFile
        try:
            try:
                with open(styleFile, 'r', encoding='utf-8') as style:
                    self.setStyleSheet(style.read())
            except:
                with open(styleFile, 'r', encoding='gbk') as style:
                    self.setStyleSheet(style.read())
        except:
            QMessageBox.warning(self, self.tr('主题载入错误'), self.tr('未能成功载入主题，请确保软件根目录有 "style.css" 文件存在。'))

    def keyPressEvent(self, event) -> None:
        # 在按下 F5 的时候重载 style.css 主题
        if (event.key() == Qt.Key_F5):
            self.loadStyleSheet()
            self.status.showMessage('已成功更新主题', 800)

    def onUpdateText(self, text):
        """Write console output to text widget."""

        cursor = self.consoleTab.consoleEditBox.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.consoleTab.consoleEditBox.setTextCursor(cursor)
        self.consoleTab.consoleEditBox.ensureCursorVisible()

    def closeEvent(self, event):
        """Shuts down application on close."""
        # Return stdout to defaults.
        if mainWindow.ConfigTab.hideToSystemTraySwitch.isChecked():
            event.ignore()
            self.hide()
        else:
            sys.stdout = sys.__stdout__
            super().closeEvent(event)

    def _start_checker(self):
        self._update_checker = UpdateChecker()
        self._update_checker.check_for_update()
        self._update_checker.update_dialog.setParent(self)
        # Setting the dialog's parent resets its flags
        # See https://forum.qt.io/topic/10477
        self._update_checker.update_dialog.setWindowFlags(
            Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.Dialog)

class SystemTray(QSystemTrayIcon):
    def __init__(self, icon, window):
        super(SystemTray, self).__init__()
        self.window = window
        self.setIcon(icon)
        self.setParent(window)
        self.activated.connect(self.trayEvent)  # 设置托盘点击事件处理函数
        self.tray_menu = QMenu(QApplication.desktop())  # 创建菜单
        # self.RestoreAction = QAction(u'还原 ', self, triggered=self.showWindow)  # 添加一级菜单动作选项(还原主窗口)
        self.QuitAction = QAction(self.tr('退出'), self, triggered=self.quit)  # 添加一级菜单动作选项(退出程序)
        # self.StyleAction = QAction(self.tr('更新主题'), self, triggered=mainWindow.loadStyleSheet)  # 添加一级菜单动作选项(更新 QSS)
        # self.tray_menu.addAction(self.RestoreAction)  # 为菜单添加动作
        self.tray_menu.addAction(self.QuitAction)
        # self.tray_menu.addAction(self.StyleAction)
        self.setContextMenu(self.tray_menu)  # 设置系统托盘菜单
        self.show()

    def showWindow(self):
        self.window.showNormal()
        self.window.activateWindow()
        self.window.setWindowFlags(Qt.Window)
        self.window.show()

    def quit(self):
        sys.stdout = sys.__stdout__
        self.hide()
        qApp.quit()

    def trayEvent(self, reason):
        # 鼠标点击icon传递的信号会带有一个整形的值，1是表示单击右键，2是双击，3是单击左键，4是用鼠标中键点击
        if reason == 2 or reason == 3:
            if mainWindow.isMinimized() or not mainWindow.isVisible():
                # 若是最小化或者最小化到托盘，则先正常显示窗口，再变为活动窗口（暂时显示在最前面）
                self.window.showNormal()
                self.window.activateWindow()
                self.window.setWindowFlags(Qt.Window)
                self.window.show()
            else:
                # 若不是最小化，则最小化
                # self.window.showMinimized()
                # self.window.show()
                pass




############# 不同功能的 Tab ################

class FFmpegMainTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initGui()
        self.initValue()

    def initGui(self):
        self.输入输出vbox = QVBoxLayout()
        # 构造输入一、输入二和输出选项
        if True:
            # 输入1
            if True:
                self.输入1标签 = QLabel(self.tr('输入1路径：'))
                self.输入1路径框 = MyQLine()
                self.输入1路径框.setPlaceholderText(self.tr('这里输入要处理的视频、音频文件'))
                self.输入1路径框.signal.connect(self.lineEditHasDrop)
                self.输入1路径框.setToolTip(self.tr('这里输入要处理的视频、音频文件'))
                self.输入1路径框.textChanged.connect(self.generateFinalCommand)
                self.输入1选择文件按钮 = QPushButton(self.tr('选择文件'))
                self.输入1选择文件按钮.clicked.connect(self.chooseFile1ButtonClicked)
                self.输入1路径hbox = QHBoxLayout()
                self.输入1路径hbox.addWidget(self.输入1标签, 0)
                self.输入1路径hbox.addWidget(self.输入1路径框, 1)
                self.输入1路径hbox.addWidget(self.输入1选择文件按钮, 0)

                self.输入1截取时间hbox = QHBoxLayout()
                self.输入1截取时间勾选框 = QCheckBox(self.tr('截取片段'))
                self.输入1截取时间勾选框.clicked.connect(self.inputOneCutCheckboxClicked)
                self.输入1截取时间勾选框.clicked.connect(self.generateFinalCommand)
                self.输入1截取时间start标签 = QLabel(self.tr('起始时间：'))
                self.输入1截取时间start输入框 = self.CutTimeEdit()
                self.输入1截取时间start输入框.textChanged.connect(self.generateFinalCommand)
                self.输入1截取时间start输入框.setAlignment(Qt.AlignCenter)
                self.输入1截取时间end标签 = self.ClickableEndTimeLable()
                # self.输入1截取时间end标签.mousePressEvent.connect(self.generateFinalCommand)
                self.输入1截取时间end输入框 = self.CutTimeEdit()
                self.输入1截取时间end输入框.textChanged.connect(self.generateFinalCommand)
                self.输入1截取时间end输入框.setAlignment(Qt.AlignCenter)
                self.输入1截取时间hbox.addWidget(self.输入1截取时间勾选框)
                self.输入1截取时间hbox.addWidget(self.输入1截取时间start标签)
                self.输入1截取时间hbox.addWidget(self.输入1截取时间start输入框)
                self.输入1截取时间hbox.addWidget(self.输入1截取时间end标签)
                self.输入1截取时间hbox.addWidget(self.输入1截取时间end输入框)

                self.输入1截取时间start标签.setVisible(False)
                self.输入1截取时间start输入框.setVisible(False)
                self.输入1截取时间end标签.setVisible(False)
                self.输入1截取时间end输入框.setVisible(False)

                self.输入1选项hbox = QHBoxLayout()
                self.输入1选项标签 = QLabel(self.tr('输入1选项：'))
                self.输入1选项输入框 = MyQLine()
                self.输入1选项输入框.textChanged.connect(self.generateFinalCommand)
                self.输入1选项hbox.addWidget(self.输入1选项标签)
                self.输入1选项hbox.addWidget(self.输入1选项输入框)

                self.输入1vbox = QVBoxLayout()
                self.输入1vbox.addLayout(self.输入1路径hbox)
                self.输入1vbox.addLayout(self.输入1选项hbox)
                self.输入1vbox.addLayout(self.输入1截取时间hbox)

            # 输入2
            if True:
                self.输入2标签 = QLabel(self.tr('输入2路径：'))
                self.输入2路径框 = MyQLine()
                self.输入2路径框.setPlaceholderText(self.tr('输入2是选填的，只有涉及同时处理两个文件的操作才需要输入2'))
                self.输入2路径框.setToolTip(self.tr('输入2是选填的，只有涉及同时处理两个文件的操作才需要输入2'))
                self.输入2路径框.textChanged.connect(self.generateFinalCommand)
                self.输入2选择文件按钮 = QPushButton(self.tr('选择文件'))
                self.输入2选择文件按钮.clicked.connect(self.chooseFile2ButtonClicked)
                self.输入2路径hbox = QHBoxLayout()
                self.输入2路径hbox.addWidget(self.输入2标签, 0)
                self.输入2路径hbox.addWidget(self.输入2路径框, 1)
                self.输入2路径hbox.addWidget(self.输入2选择文件按钮, 0)

                self.输入2截取时间hbox = QHBoxLayout()
                self.输入2截取时间勾选框 = QCheckBox(self.tr('截取片段'))
                self.输入2截取时间勾选框.clicked.connect(self.inputTwoCutCheckboxClicked)
                self.输入2截取时间勾选框.clicked.connect(self.generateFinalCommand)
                self.输入2截取时间start标签 = QLabel(self.tr('起始时间：'))
                self.输入2截取时间start输入框 = self.CutTimeEdit()
                self.输入2截取时间start输入框.setAlignment(Qt.AlignCenter)
                self.输入2截取时间start输入框.textChanged.connect(self.generateFinalCommand)
                self.输入2截取时间end标签 = self.ClickableEndTimeLable()
                self.输入2截取时间end输入框 = self.CutTimeEdit()
                self.输入2截取时间end输入框.setAlignment(Qt.AlignCenter)
                self.输入2截取时间end输入框.textChanged.connect(self.generateFinalCommand)
                self.输入2截取时间hbox.addWidget(self.输入2截取时间勾选框)
                self.输入2截取时间hbox.addWidget(self.输入2截取时间start标签)
                self.输入2截取时间hbox.addWidget(self.输入2截取时间start输入框)
                self.输入2截取时间hbox.addWidget(self.输入2截取时间end标签)
                self.输入2截取时间hbox.addWidget(self.输入2截取时间end输入框)
                self.输入2截取时间start标签.setVisible(False)
                self.输入2截取时间start输入框.setVisible(False)
                self.输入2截取时间end标签.setVisible(False)
                self.输入2截取时间end输入框.setVisible(False)

                self.输入2选项hbox = QHBoxLayout()
                self.输入2选项标签 = QLabel(self.tr('输入2选项：'))
                self.输入2选项输入框 = MyQLine()
                self.输入2选项输入框.textChanged.connect(self.generateFinalCommand)
                self.输入2选项hbox.addWidget(self.输入2选项标签)
                self.输入2选项hbox.addWidget(self.输入2选项输入框)

                self.输入2vbox = QVBoxLayout()
                self.输入2vbox.addLayout(self.输入2路径hbox)
                self.输入2vbox.addLayout(self.输入2选项hbox)
                self.输入2vbox.addLayout(self.输入2截取时间hbox)

            self.timeValidator = QRegExpValidator(self)
            self.timeValidator.setRegExp(QRegExp(r'[0-9]{0,2}:?[0-9]{0,2}:?[0-9]{0,2}\.?[0-9]{0,2}'))
            self.输入1截取时间start输入框.setValidator(self.timeValidator)
            self.输入1截取时间end输入框.setValidator(self.timeValidator)
            self.输入2截取时间start输入框.setValidator(self.timeValidator)
            self.输入2截取时间end输入框.setValidator(self.timeValidator)

            # 输出
            if True:
                self.输出标签 = QLabel(self.tr('输出：'))
                self.输出路径框 = MyQLine()
                self.输出路径框.setPlaceholderText(self.tr('文件名填什么后缀，就会输出什么格式'))
                self.输出路径框.setToolTip(self.tr('这里填写输出文件保存路径'))
                self.输出路径框.textChanged.connect(self.generateFinalCommand)
                self.输出选择文件按钮 = QPushButton(self.tr('选择保存位置'))
                self.输出选择文件按钮.clicked.connect(self.chooseOutputFileButtonClicked)
                self.输出路径hbox = QHBoxLayout()
                self.输出路径hbox.addWidget(self.输出标签, 0)
                self.输出路径hbox.addWidget(self.输出路径框, 1)
                self.输出路径hbox.addWidget(self.输出选择文件按钮, 0)

                self.输出分辨率hbox = QHBoxLayout()
                self.输出分辨率勾选框 = QCheckBox(self.tr('新分辨率'))
                self.输出分辨率勾选框.clicked.connect(self.outputResolutionCheckboxClicked)
                self.输出分辨率勾选框.clicked.connect(self.generateFinalCommand)

                self.X轴分辨率输入框 = self.ResolutionEdit()
                self.X轴分辨率输入框.setAlignment(Qt.AlignCenter)
                self.X轴分辨率输入框.textChanged.connect(self.generateFinalCommand)
                self.分辨率乘号标签 = self.ClickableResolutionTimesLable()
                self.Y轴分辨率输入框 = self.ResolutionEdit()
                self.Y轴分辨率输入框.setAlignment(Qt.AlignCenter)
                self.Y轴分辨率输入框.textChanged.connect(self.generateFinalCommand)
                self.分辨率预设按钮 = QPushButton(self.tr('分辨率预设'))
                self.分辨率预设按钮.clicked.connect(self.resolutionPresetButtonClicked)
                self.X轴分辨率输入框.setVisible(False)
                self.分辨率乘号标签.setVisible(False)
                self.Y轴分辨率输入框.setVisible(False)
                self.分辨率预设按钮.setVisible(False)

                self.输出分辨率hbox.addWidget(self.输出分辨率勾选框, 0)
                self.输出分辨率hbox.addWidget(self.X轴分辨率输入框, 1)
                self.输出分辨率hbox.addWidget(self.分辨率乘号标签, 0)
                self.输出分辨率hbox.addWidget(self.Y轴分辨率输入框, 1)
                self.输出分辨率hbox.addWidget(self.分辨率预设按钮, 0)

                self.输出选项标签 = QLabel(self.tr('输出选项：'))
                self.输出选项输入框 = QPlainTextEdit()
                self.输出选项输入框.textChanged.connect(self.generateFinalCommand)
                self.输出选项输入框.setMaximumHeight(100)
                self.输出选项hbox = QHBoxLayout()
                self.输出选项hbox.addWidget(self.输出选项标签)
                self.输出选项hbox.addWidget(self.输出选项输入框)

                self.输出vbox = QVBoxLayout()
                self.输出vbox.addLayout(self.输出路径hbox)
                self.输出vbox.addLayout(self.输出分辨率hbox)
                self.输出vbox.addLayout(self.输出选项hbox)

            # 输入输出放到一个布局
            if True:
                self.主布局 = QVBoxLayout()
                self.主布局.addLayout(self.输入1vbox)
                self.主布局.addSpacing(30)
                self.主布局.addLayout(self.输入2vbox)
                self.主布局.addSpacing(30)
                self.主布局.addLayout(self.输出vbox)

            # 输入输出布局放到一个控件
            self.主布局控件 = QWidget()
            self.主布局控件.setLayout(self.主布局)

        # 预设列表
        if True:
            self.预设列表提示标签 = QLabel(self.tr('选择预设：'))
            self.预设列表 = QListWidget()
            self.预设列表.itemClicked.connect(self.presetItemSelected)
            self.预设列表.itemDoubleClicked.connect(self.addPresetButtonClicked)

            self.添加预设按钮 = QPushButton('+')
            self.删除预设按钮 = QPushButton('-')
            # self.修改预设按钮 = QPushButton('修改选中预设')
            self.上移预设按钮 = QPushButton('↑')
            self.下移预设按钮 = QPushButton('↓')
            self.查看预设帮助按钮 = QPushButton(self.tr('查看该预设帮助'))
            self.预设vbox = QGridLayout()
            self.预设vbox.addWidget(self.预设列表提示标签, 0, 0, 1, 1)
            self.预设vbox.addWidget(self.预设列表, 1, 0, 1, 2)
            self.预设vbox.addWidget(self.上移预设按钮, 2, 0, 1, 1)
            self.预设vbox.addWidget(self.下移预设按钮, 2, 1, 1, 1)
            self.预设vbox.addWidget(self.添加预设按钮, 3, 0, 1, 1)
            self.预设vbox.addWidget(self.删除预设按钮, 3, 1, 1, 1)
            # self.预设vbox.addWidget(self.修改预设按钮, 3, 0, 1, 1)
            self.预设vbox.addWidget(self.查看预设帮助按钮, 4, 0, 1, 2)
            self.预设vbox控件 = QWidget()
            self.预设vbox控件.setLayout(self.预设vbox)

            self.上移预设按钮.clicked.connect(self.upwardButtonClicked)
            self.下移预设按钮.clicked.connect(self.downwardButtonClicked)
            self.添加预设按钮.clicked.connect(self.addPresetButtonClicked)
            self.删除预设按钮.clicked.connect(self.delPresetButtonClicked)
            # self.修改预设按钮.clicked.connect(self.modifyPresetButtonClicked)
            self.查看预设帮助按钮.clicked.connect(self.checkPresetHelpButtonClicked)

        # 总命令编辑框
        if True:
            self.总命令编辑框 = QPlainTextEdit()
            self.总命令编辑框.setPlaceholderText(self.tr('这里是自动生成的总命令'))

            self.总命令编辑框.setMaximumHeight(200)
            self.总命令执行按钮 = QPushButton(self.tr('运行'))
            self.总命令执行按钮.clicked.connect(self.runFinalCommandButtonClicked)
            self.总命令部分vbox = QVBoxLayout()
            self.总命令部分vbox.addWidget(self.总命令编辑框)
            self.总命令部分vbox.addWidget(self.总命令执行按钮)
            self.总命令部分vbox控件 = QWidget()
            self.总命令部分vbox控件.setLayout(self.总命令部分vbox)

        # 放置三个主要部件
        if True:
            # 分割线左边放输入输出布局，右边放列表
            self.竖分割线 = QSplitter(Qt.Horizontal)
            self.竖分割线.addWidget(self.主布局控件)
            self.竖分割线.addWidget(self.预设vbox控件)

            self.横分割线 = QSplitter(Qt.Vertical)
            self.横分割线.addWidget(self.竖分割线)
            self.横分割线.addWidget(self.总命令部分vbox控件)

            # 用一个横向布局，将分割线放入
            self.最顶层布局hbox = QHBoxLayout()
            self.最顶层布局hbox.addWidget(self.横分割线)

            # 将本页面的布局设为上面的横向布局
            self.setLayout(self.最顶层布局hbox)

    def initValue(self):
        # 检查杂项文件夹是否存在
        self.createMiscFolder()

        # 检查数据库是否存在
        self.createDB()

        # 刷新预设列表
        self.refreshList()

        # 定义一个变量，用于判断输入文件，输出文件的选项是否有被手工修改过
        self.commandOptionsChanged = False

    # 如果输入文件是拖进去的
    def lineEditHasDrop(self, path):
        outputName = os.path.splitext(path)[0] + '_out' + os.path.splitext(path)[1]
        self.输出路径框.setText(outputName)
        return True

    # 选择输入文件1
    def chooseFile1ButtonClicked(self):
        filename = QFileDialog().getOpenFileName(self, '打开文件', None, '所有文件(*)')
        if filename[0] != '':
            self.输入1路径框.setText(filename[0])
            outputName = re.sub(r'(\.[^\.]+)$', r'_out\1', filename[0])
            self.输出路径框.setText(outputName)
        self.commandOptionsChanged = False
        return True

    # 选择输入文件2
    def chooseFile2ButtonClicked(self):
        filename = QFileDialog().getOpenFileName(self, '打开文件', None, '所有文件(*)')
        if filename[0] != '':
            self.输入2路径框.setText(filename[0])
        self.commandOptionsChanged = False
        return True

    # 选择输出文件
    def chooseOutputFileButtonClicked(self):
        filename = QFileDialog().getSaveFileName(self, '设置输出保存的文件名', '输出视频.mp4', '所有文件(*)')
        self.输出路径框.setText(filename[0])
        self.commandOptionsChanged = False
        return True

    # 输出一截取勾选框
    def inputOneCutCheckboxClicked(self):
        if self.输入1截取时间勾选框.isChecked():
            self.输入1截取时间start标签.setVisible(True)
            self.输入1截取时间start输入框.setVisible(True)
            self.输入1截取时间end标签.setVisible(True)
            self.输入1截取时间end输入框.setVisible(True)
        else:
            self.输入1截取时间start标签.setVisible(False)
            self.输入1截取时间start输入框.setVisible(False)
            self.输入1截取时间end标签.setVisible(False)
            self.输入1截取时间end输入框.setVisible(False)
        return True

    # 输出2截取勾选框
    def inputTwoCutCheckboxClicked(self):
        if self.输入2截取时间勾选框.isChecked():
            self.输入2截取时间start标签.setVisible(True)
            self.输入2截取时间start输入框.setVisible(True)
            self.输入2截取时间end标签.setVisible(True)
            self.输入2截取时间end输入框.setVisible(True)
        else:
            self.输入2截取时间start标签.setVisible(False)
            self.输入2截取时间start输入框.setVisible(False)
            self.输入2截取时间end标签.setVisible(False)
            self.输入2截取时间end输入框.setVisible(False)
        return True

        # 输出分辨率勾选框

    # 输出分辨率勾选框
    def outputResolutionCheckboxClicked(self):
        if self.输出分辨率勾选框.isChecked():
            self.X轴分辨率输入框.setVisible(True)
            self.分辨率乘号标签.setVisible(True)
            self.Y轴分辨率输入框.setVisible(True)
            self.分辨率预设按钮.setVisible(True)
        else:
            self.X轴分辨率输入框.setVisible(False)
            self.分辨率乘号标签.setVisible(False)
            self.Y轴分辨率输入框.setVisible(False)
            self.分辨率预设按钮.setVisible(False)
        return True

    def resolutionPresetButtonClicked(self):
        self.ResolutionDialog()
        return True

    # 自动生成总命令
    def generateFinalCommand(self):
        self.finalCommand = 'ffmpeg -y -hide_banner'
        inputOnePath = self.输入1路径框.text()
        if inputOnePath != '':  # 只有有输入文件1时才会继续生成命令
            self.commandOptionsChanged = True
            inputOneCutSwitch = self.输入1截取时间勾选框.isChecked()
            if inputOneCutSwitch != 0:
                inputOneStartTime = self.输入1截取时间start输入框.text()
                if inputOneStartTime != '':
                    self.finalCommand = self.finalCommand + ' ' + '-ss %s' % (inputOneStartTime)
                inputOneEndTime = self.输入1截取时间end输入框.text()
                if inputOneEndTime != '':
                    if self.输入1截取时间end标签.text() == '截取时长：':
                        self.finalCommand = self.finalCommand + ' ' + '-t %s' % (inputOneEndTime)
                    elif self.输入1截取时间end标签.text() == '截止时刻：':
                        self.finalCommand = self.finalCommand + ' ' + '-to %s' % (inputOneEndTime)
            inputOneOption = self.输入1选项输入框.text()
            if inputOneOption != '':
                self.finalCommand = self.finalCommand + ' ' + inputOneOption

            self.finalCommand = self.finalCommand + ' ' + '-i "%s"' % (inputOnePath)

            inputTwoPath = self.输入2路径框.text()
            if inputTwoPath != '':  # 只有有输入文件2时才会继续生成命令
                inputTwoCutSwitch = self.输入2截取时间勾选框.isChecked()
                if inputTwoCutSwitch != 0:
                    inputTwoStartTime = self.输入2截取时间start输入框.text()
                    if inputTwoStartTime != '':
                        self.finalCommand = self.finalCommand + ' ' + '-ss %s' % (inputTwoStartTime)
                    inputTwoEndTime = self.输入2截取时间end输入框.text()
                    if inputTwoEndTime != '':
                        if self.输入2截取时间end标签.text() == '截取时长：':
                            self.finalCommand = self.finalCommand + ' ' + '-t %s' % (inputTwoEndTime)
                        elif self.输入2截取时间end标签.text() == '截止时刻：':
                            self.finalCommand = self.finalCommand + ' ' + '-to %s' % (inputTwoEndTime)
                inputTwoOption = self.输入2选项输入框.text()
                if inputTwoOption != '':
                    self.finalCommand = self.finalCommand + ' ' + inputTwoOption
                self.finalCommand = self.finalCommand + ' ' + '-i "%s"' % (inputTwoPath)

            outputOption = self.输出选项输入框.toPlainText()
            if self.输出分辨率勾选框.isChecked() != 0:
                outputResizeX = self.X轴分辨率输入框.text()
                if outputResizeX == '':
                    outputResizeX = '-2'
                outputResizeY = self.Y轴分辨率输入框.text()
                if outputResizeY == '':
                    outputResizeY = '-2'
                if '-vf' not in self.finalCommand and 'scale' not in outputOption and 'filter' not in outputOption:
                    # print(False)
                    self.finalCommand = self.finalCommand + ' ' + '-vf "scale=%s:%s"' % (outputResizeX, outputResizeY)
                elif 'scale' in outputOption:
                    # print(True)
                    outputOption = re.sub('[-0-9]+:[-0-9]+', '%s:%s' % (outputResizeX, outputResizeY), outputOption)
            if outputOption != '':
                self.finalCommand = self.finalCommand + ' ' + outputOption
            outputPath = self.输出路径框.text()
            if outputPath != '':
                self.finalCommand = self.finalCommand + ' ' + '"%s"' % (outputPath)

            if self.预设列表.currentRow() > -1:
                if self.extraCode != '' and self.extraCode != None:
                    try:
                        exec(self.extraCode)
                    except:
                        pass

            self.总命令编辑框.setPlainText(self.finalCommand)
        return True

    # 点击运行按钮
    def runFinalCommandButtonClicked(self):
        finalCommand = self.总命令编辑框.toPlainText()
        outputPath = self.输出路径框.text()
        if os.path.exists(outputPath):
            overwrite = QMessageBox.information(
                self, self.tr('覆盖确认'), self.tr('输出路径对应的文件已存在，是否要覆盖？'),
                QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
            if overwrite != QMessageBox.Yes:
                return
        if finalCommand != '':
            execute(finalCommand)

    # 检查杂项文件夹是否存在
    def createMiscFolder(self):
        if not os.path.exists('./misc'):
            os.mkdir('./misc')

    # 检查数据库是否存在
    def createDB(self):
        ########改用主数据库
        cursor = conn.cursor()
        result = cursor.execute('select * from sqlite_master where name = "%s";' % (presetTableName))
        # 将初始预设写入数据库
        if result.fetchone() == None:
            cursor.execute('''create table %s (
                            id integer primary key autoincrement, 
                            name text, 
                            inputOneOption TEXT, 
                            inputTwoOption TEXT, 
                            outputExt TEXT, 
                            outputOption TEXT, 
                            extraCode TEXT, 
                            description TEXT
                            )''' % (presetTableName))
            # print('新建了表单')

            # 新建一个空预设
            # 不使用预设
            presetName = self.tr('不使用预设')
            cursor.execute('''
                            insert into %s 
                            (name, outputOption) 
                            values (
                            '%s',
                            '-c copy'
                            );'''
                           % (presetTableName, presetName))

            # h264 压制
            presetName = self.tr('H264压制')
            description = '''<body><h4>H264压制视频</h4><p>输入文件一，模板中选择 Video ( h264 ) ，输出选项会自动设置好，点击 Run ，粘贴编码，等待压制完成即可。</p><p> </p><h4>选项帮助：</h4><h5>输出文件选项：</h5><p>-c:v 设置视频编码器</p><p>-crf 恒定视频质量的参数</p><p>-preset 压制速度，可选项：ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow, placebo</p><p>-qcomp 量化曲线压缩因子（Quantizer curve compression factor）</p><p>-psy-rd 用 psy-rd:psy-trellis 的格式设置 心理视觉优化强度（ strength of psychovisual optimization, in psy-rd:psy-trellis format）</p><p>-aq-mode 设置 AQ 方法，可选值为：</p><ul><li>none (<em>0</em>) 帧内宏块全部使用同一或者固定的表</li><li>variance (<em>1</em>) 使用方差动态计算每个宏块的</li><li>autovariance (<em>2</em>) 方差自适应模式，会先遍历一次全部宏块，统计出一些中间参数，之后利用这些参数，对每个宏块计算 </li></ul><p>-aq-strength 设置 AQ 强度，在平面和纹理区域 减少 方块和模糊。</p><p> </p><p> </p><h4>注意事项</h4><p>注意，压制视频的话，输入文件放一个就行了哈，别放两个输入，FFmpeg 会自动把最高分辨率的视频流和声道数最多的音频流合并输出的。</p><p> </p><h4>相关科普</h4><p>压制过程中你可以从命令行看到实时压制速度、总码率、体积、压制到视频几分几秒了。</p><p>相关解释：H264是一个很成熟的视频编码格式，兼容性也很好，一般你所见到的视频多数都是这个编码，小白压制视频无脑选这个就行了。</p><p>这个参数下，画质和体积能得到较好的平衡，一般能把手机相机拍摄的视频压制到原来体积的1/3左右，甚至更小，画质也没有明显的损失。</p><p>控制视频大小有两种方法：</p><ul><li><p>恒定画面质量，可变码率。也就是 crf 方式</p></li><p>这时，编码器会根据你要求的画面质量，自动分配码率，给复杂的画面部分多分配点码率，给简单的画面少分配点码率，可以得到画面质量均一的输出视频，这是最推荐的压制方式。不过无法准确预测输出文件的大小。假如你的视频全程都是非常复杂、包含大量背景运动的画面，那么可能压制出来的视频，比原视频还要大。这里的压制方式用的就是 恒定画面质量 的方式。</p><li><p>恒定码率</p></li></ul><p>这时，编码器会根据你的要求，给每一秒都分配相同的码率，可以准确预测输出文件的大小。但是，由于码率恒定，可能有些复杂的片段，你分配的码率不够用，就会画质下降，有些静态部分多的画面，就浪费了很多码率，所以一般不推荐用。如果你想用这个方案，请参阅 <a href='#控制码率压制视频'>控制码率压制视频</a> </p><p>针对恒定码率的缺点，有个改进方案就是 2-pass （二压），详见 <a href='#h264 二压视频（两次操作）'>h264 二压视频（两次操作）</a> </p><p>此处输出选项里的 -crf 23 是画质控制参数。取值 0 - 51 ，越小画质越高，同时体积越大。 0 代表无损画质，体积超大。一般认为， -crf 18 的时候，人眼就几乎无法看出画质有损失了，大于 -crf 28 的时候，人眼就开始看到比较明显的画质损失。没有特殊要求的话，默认用 -crf 23 就行了。压制画质要求很高的视频就用 -crf 18 。</p><p>此处输出选项里的 -preset medium 代表压制编码速度适中，可选值有 ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow, placebo ，设置越慢，压制时间越长，画质控制越出色，设置越快，信息丢失就越严重，图像质量越差。</p><p>为什么 placebo 是纯粹的浪费时间？ </p><p>相同码率下，相比于 veryslow，placebo 只提升不到 1% 的视频质量（同样码率下），但消耗非常多的时间。veryslow 比 slower 提升 3% ； slower 比 slow 提升 5% ，slow 比 medium 提升 5%-10% 。</p><p>相同码率下，相较于 medium：slow 编码所需时间增加大约 40% ；到 slower 增加大约 100% ，到 veryslow 增加大约 280% 。</p><p>相同码率下，相较于 medium ： fast 节约 10% 编码时间； faster 节约 25% ； ultrafast 节约 55%（但代价是更低的画质）</p><p>如果你的原视频是 rgb 像素格式的，建议使用 -c:v libx264rgb ，来避免转化成 yuv420 时的画质损失。</p></body>'''
            cursor.execute('''
                            insert into %s 
                            (name, outputOption, description) 
                            values (
                            '%s', 
                            '-c:v libx264 -crf 23 -preset slow -qcomp 0.5 -psy-rd 0.3:0 -aq-mode 2 -aq-strength 0.8 -b:a 256k',
                            '%s'
                            );'''
                           % (presetTableName, presetName, description.replace("'", "''")))

            # h264 压制 Intel 硬件加速
            presetName = self.tr('H264压制 Intel 硬件加速')
            description = '''<body><p>关于使用硬件加速：</p><p>目前硬件加速支持两种编码格式：H264 和 H265</p><p>有3种加速方法，分别对应三家的硬件：Inter、AMD、Nvidia</p><p>不过在苹果电脑上，不管你用的哪家的硬件，都是使用 videotoolbox 编码器。</p><p>需要注意的是，即便你的电脑拥有 Nvidia 显卡，可能也用不了 Nvidia 的硬件加速编码，因为 Nvidia 硬件加速依赖于显卡内部的一种特定的 GPU 的物理部分，专用于编码。只有在 GTX10 和 RTX20 以上的显卡才搭载有这个物理部分。</p><p>使用硬件编码器进行编码，只需要将输出选项中的编码器改成硬件编码器即可，其中：</p><ul><li><code>-c:v h264_qsv</code> 对应 Intel H264 编码</li><li><code>-c:v h264_amf</code> 对应 AMD H264 编码</li><li><code>-c:v h264_nvenc</code> 对应 Nvidia H264 编码</li><li><code>-c:v h264_videotoolbox</code> 对应苹果电脑的 H264 编码</li><li><code>-c:v hevc_qsv</code> 对应 Intel H265 编码</li><li><code>-c:v hevc_amf</code> 对应 AMDH265 编码</li><li><code>-c:v hevc_nvenc</code> 对应 Nvidia H265 编码</li><li><code>-c:v hevc_videotoolbox</code> 对应苹果电脑的 H265 编码</li></ul><p><code>-c:v</code> 表示视频（Video）的编码器（codec）</p><p>在使用硬件加速编码器的时候，控制输出视频的质量是使用 <code>qscale</code> 参数，他的数值可以从 <code>0.1 - 255</code> 不等，数值越小，画质越高，码率越大，输出文件体积越大。同一个数值对于不同的编码器画质的影响效果不同。所以你需要自己测试，在玛律大小和视频画质之间找到一个平衡的 <code>qscale</code> 数值。</p><p>目前所有的硬件加速选项都是类似这样的：<code>-c:v h264_qsv -qscale 15</code> ，这表示使用英特尔 h264 硬件加速编码器，视频质量参数为15。你可以更改里面的数值，以达到你期望的画质效果。</p></body>'''
            cursor.execute('''
                            insert into %s 
                            (name, outputOption, description) 
                            values (
                            '%s', 
                            '-c:v h264_qsv -qscale 15 -b:a 256k',
                            '%s'
                            );'''
                           % (presetTableName, presetName, description.replace("'", "''")))

            # h264 压制 AMD 硬件加速
            presetName = self.tr('H264压制 AMD 硬件加速')
            description = '''<body><p>关于使用硬件加速：</p><p>目前硬件加速支持两种编码格式：H264 和 H265</p><p>有3种加速方法，分别对应三家的硬件：Inter、AMD、Nvidia</p><p>不过在苹果电脑上，不管你用的哪家的硬件，都是使用 videotoolbox 编码器。</p><p>需要注意的是，即便你的电脑拥有 Nvidia 显卡，可能也用不了 Nvidia 的硬件加速编码，因为 Nvidia 硬件加速依赖于显卡内部的一种特定的 GPU 的物理部分，专用于编码。只有在 GTX10 和 RTX20 以上的显卡才搭载有这个物理部分。</p><p>使用硬件编码器进行编码，只需要将输出选项中的编码器改成硬件编码器即可，其中：</p><ul><li><code>-c:v h264_qsv</code> 对应 Intel H264 编码</li><li><code>-c:v h264_amf</code> 对应 AMD H264 编码</li><li><code>-c:v h264_nvenc</code> 对应 Nvidia H264 编码</li><li><code>-c:v h264_videotoolbox</code> 对应苹果电脑的 H264 编码</li><li><code>-c:v hevc_qsv</code> 对应 Intel H265 编码</li><li><code>-c:v hevc_amf</code> 对应 AMDH265 编码</li><li><code>-c:v hevc_nvenc</code> 对应 Nvidia H265 编码</li><li><code>-c:v hevc_videotoolbox</code> 对应苹果电脑的 H265 编码</li></ul><p><code>-c:v</code> 表示视频（Video）的编码器（codec）</p><p>在使用硬件加速编码器的时候，控制输出视频的质量是使用 <code>qscale</code> 参数，他的数值可以从 <code>0.1 - 255</code> 不等，数值越小，画质越高，码率越大，输出文件体积越大。同一个数值对于不同的编码器画质的影响效果不同。所以你需要自己测试，在玛律大小和视频画质之间找到一个平衡的 <code>qscale</code> 数值。</p><p>目前所有的硬件加速选项都是类似这样的：<code>-c:v h264_qsv -qscale 15</code> ，这表示使用英特尔 h264 硬件加速编码器，视频质量参数为15。你可以更改里面的数值，以达到你期望的画质效果。</p></body>'''
            cursor.execute('''
                            insert into %s 
                            (name, outputOption, description) 
                            values (
                            '%s', 
                            '-c:v h264_amf -qscale 15 -b:a 256k',
                            '%s'
                            );'''
                           % (presetTableName, presetName, description.replace("'", "''")))

            # h264 压制 Nvidia 硬件加速
            presetName = self.tr('H264压制 Nvidia 硬件加速')
            description = '''<body><p>关于使用硬件加速：</p><p>目前硬件加速支持两种编码格式：H264 和 H265</p><p>有3种加速方法，分别对应三家的硬件：Inter、AMD、Nvidia</p><p>不过在苹果电脑上，不管你用的哪家的硬件，都是使用 videotoolbox 编码器。</p><p>需要注意的是，即便你的电脑拥有 Nvidia 显卡，可能也用不了 Nvidia 的硬件加速编码，因为 Nvidia 硬件加速依赖于显卡内部的一种特定的 GPU 的物理部分，专用于编码。只有在 GTX10 和 RTX20 以上的显卡才搭载有这个物理部分。</p><p>使用硬件编码器进行编码，只需要将输出选项中的编码器改成硬件编码器即可，其中：</p><ul><li><code>-c:v h264_qsv</code> 对应 Intel H264 编码</li><li><code>-c:v h264_amf</code> 对应 AMD H264 编码</li><li><code>-c:v h264_nvenc</code> 对应 Nvidia H264 编码</li><li><code>-c:v h264_videotoolbox</code> 对应苹果电脑的 H264 编码</li><li><code>-c:v hevc_qsv</code> 对应 Intel H265 编码</li><li><code>-c:v hevc_amf</code> 对应 AMDH265 编码</li><li><code>-c:v hevc_nvenc</code> 对应 Nvidia H265 编码</li><li><code>-c:v hevc_videotoolbox</code> 对应苹果电脑的 H265 编码</li></ul><p><code>-c:v</code> 表示视频（Video）的编码器（codec）</p><p>在使用硬件加速编码器的时候，控制输出视频的质量是使用 <code>qscale</code> 参数，他的数值可以从 <code>0.1 - 255</code> 不等，数值越小，画质越高，码率越大，输出文件体积越大。同一个数值对于不同的编码器画质的影响效果不同。所以你需要自己测试，在玛律大小和视频画质之间找到一个平衡的 <code>qscale</code> 数值。</p><p>目前所有的硬件加速选项都是类似这样的：<code>-c:v h264_qsv -qscale 15</code> ，这表示使用英特尔 h264 硬件加速编码器，视频质量参数为15。你可以更改里面的数值，以达到你期望的画质效果。</p></body>'''
            cursor.execute('''
                            insert into %s 
                            (name, outputOption, description) 
                            values (
                            '%s', 
                            '-c:v h264_nvenc -qscale 15 -b:a 256k',
                            '%s'
                            );'''
                           % (presetTableName, presetName, description.replace("'", "''")))

            # h264 压制 Mac 硬件加速
            presetName = self.tr('H264压制 Mac 硬件加速')
            description = '''<body><p>关于使用硬件加速：</p><p>目前硬件加速支持两种编码格式：H264 和 H265</p><p>有3种加速方法，分别对应三家的硬件：Inter、AMD、Nvidia</p><p>不过在苹果电脑上，不管你用的哪家的硬件，都是使用 videotoolbox 编码器。</p><p>需要注意的是，即便你的电脑拥有 Nvidia 显卡，可能也用不了 Nvidia 的硬件加速编码，因为 Nvidia 硬件加速依赖于显卡内部的一种特定的 GPU 的物理部分，专用于编码。只有在 GTX10 和 RTX20 以上的显卡才搭载有这个物理部分。</p><p>使用硬件编码器进行编码，只需要将输出选项中的编码器改成硬件编码器即可，其中：</p><ul><li><code>-c:v h264_qsv</code> 对应 Intel H264 编码</li><li><code>-c:v h264_amf</code> 对应 AMD H264 编码</li><li><code>-c:v h264_nvenc</code> 对应 Nvidia H264 编码</li><li><code>-c:v h264_videotoolbox</code> 对应苹果电脑的 H264 编码</li><li><code>-c:v hevc_qsv</code> 对应 Intel H265 编码</li><li><code>-c:v hevc_amf</code> 对应 AMDH265 编码</li><li><code>-c:v hevc_nvenc</code> 对应 Nvidia H265 编码</li><li><code>-c:v hevc_videotoolbox</code> 对应苹果电脑的 H265 编码</li></ul><p><code>-c:v</code> 表示视频（Video）的编码器（codec）</p><p>在使用硬件加速编码器的时候，控制输出视频的质量是使用 <code>qscale</code> 参数，他的数值可以从 <code>0.1 - 255</code> 不等，数值越小，画质越高，码率越大，输出文件体积越大。同一个数值对于不同的编码器画质的影响效果不同。所以你需要自己测试，在玛律大小和视频画质之间找到一个平衡的 <code>qscale</code> 数值。</p><p>目前所有的硬件加速选项都是类似这样的：<code>-c:v h264_qsv -qscale 15</code> ，这表示使用英特尔 h264 硬件加速编码器，视频质量参数为15。你可以更改里面的数值，以达到你期望的画质效果。</p></body>'''
            cursor.execute('''
                                        insert into %s 
                                        (name, outputOption, description) 
                                        values (
                                        '%s', 
                                        '-c:v h264_videotoolbox -qscale 15 -b:a 256k',
                                        '%s'
                                        );'''
                           % (presetTableName, presetName, description.replace("'", "''")))

            # h265压制
            presetName = self.tr('H265压制')
            description = '''h265 编码'''
            cursor.execute('''
                            insert into %s 
                            (name, outputOption, description) 
                            values (
                            "%s", 
                            "-c:v libx265 -crf 28 -b:a 256k",
                            '%s'
                            );'''
                           % (presetTableName, presetName, description.replace("'", "''")))

            # h265压制 Intel 硬件加速
            presetName = self.tr('H265压制 Intel 硬件加速')
            description = '''<body><p>关于使用硬件加速：</p><p>目前硬件加速支持两种编码格式：H264 和 H265</p><p>有3种加速方法，分别对应三家的硬件：Inter、AMD、Nvidia</p><p>不过在苹果电脑上，不管你用的哪家的硬件，都是使用 videotoolbox 编码器。</p><p>需要注意的是，即便你的电脑拥有 Nvidia 显卡，可能也用不了 Nvidia 的硬件加速编码，因为 Nvidia 硬件加速依赖于显卡内部的一种特定的 GPU 的物理部分，专用于编码。只有在 GTX10 和 RTX20 以上的显卡才搭载有这个物理部分。</p><p>使用硬件编码器进行编码，只需要将输出选项中的编码器改成硬件编码器即可，其中：</p><ul><li><code>-c:v h264_qsv</code> 对应 Intel H264 编码</li><li><code>-c:v h264_amf</code> 对应 AMD H264 编码</li><li><code>-c:v h264_nvenc</code> 对应 Nvidia H264 编码</li><li><code>-c:v h264_videotoolbox</code> 对应苹果电脑的 H264 编码</li><li><code>-c:v hevc_qsv</code> 对应 Intel H265 编码</li><li><code>-c:v hevc_amf</code> 对应 AMDH265 编码</li><li><code>-c:v hevc_nvenc</code> 对应 Nvidia H265 编码</li><li><code>-c:v hevc_videotoolbox</code> 对应苹果电脑的 H265 编码</li></ul><p><code>-c:v</code> 表示视频（Video）的编码器（codec）</p><p>在使用硬件加速编码器的时候，控制输出视频的质量是使用 <code>qscale</code> 参数，他的数值可以从 <code>0.1 - 255</code> 不等，数值越小，画质越高，码率越大，输出文件体积越大。同一个数值对于不同的编码器画质的影响效果不同。所以你需要自己测试，在玛律大小和视频画质之间找到一个平衡的 <code>qscale</code> 数值。</p><p>目前所有的硬件加速选项都是类似这样的：<code>-c:v h264_qsv -qscale 15</code> ，这表示使用英特尔 h264 硬件加速编码器，视频质量参数为15。你可以更改里面的数值，以达到你期望的画质效果。</p></body>'''
            cursor.execute('''
                            insert into %s 
                            (name, outputOption, description) 
                            values (
                            "%s", 
                            "-c:v hevc_qsv -qscale 15 -b:a 256k",
                            '%s'
                            );'''
                           % (presetTableName, presetName, description.replace("'", "''")))

            # h265压制 AMD 硬件加速
            presetName = self.tr('H265压制 AMD 硬件加速')
            description = '''<body><p>关于使用硬件加速：</p><p>目前硬件加速支持两种编码格式：H264 和 H265</p><p>有3种加速方法，分别对应三家的硬件：Inter、AMD、Nvidia</p><p>不过在苹果电脑上，不管你用的哪家的硬件，都是使用 videotoolbox 编码器。</p><p>需要注意的是，即便你的电脑拥有 Nvidia 显卡，可能也用不了 Nvidia 的硬件加速编码，因为 Nvidia 硬件加速依赖于显卡内部的一种特定的 GPU 的物理部分，专用于编码。只有在 GTX10 和 RTX20 以上的显卡才搭载有这个物理部分。</p><p>使用硬件编码器进行编码，只需要将输出选项中的编码器改成硬件编码器即可，其中：</p><ul><li><code>-c:v h264_qsv</code> 对应 Intel H264 编码</li><li><code>-c:v h264_amf</code> 对应 AMD H264 编码</li><li><code>-c:v h264_nvenc</code> 对应 Nvidia H264 编码</li><li><code>-c:v h264_videotoolbox</code> 对应苹果电脑的 H264 编码</li><li><code>-c:v hevc_qsv</code> 对应 Intel H265 编码</li><li><code>-c:v hevc_amf</code> 对应 AMDH265 编码</li><li><code>-c:v hevc_nvenc</code> 对应 Nvidia H265 编码</li><li><code>-c:v hevc_videotoolbox</code> 对应苹果电脑的 H265 编码</li></ul><p><code>-c:v</code> 表示视频（Video）的编码器（codec）</p><p>在使用硬件加速编码器的时候，控制输出视频的质量是使用 <code>qscale</code> 参数，他的数值可以从 <code>0.1 - 255</code> 不等，数值越小，画质越高，码率越大，输出文件体积越大。同一个数值对于不同的编码器画质的影响效果不同。所以你需要自己测试，在玛律大小和视频画质之间找到一个平衡的 <code>qscale</code> 数值。</p><p>目前所有的硬件加速选项都是类似这样的：<code>-c:v h264_qsv -qscale 15</code> ，这表示使用英特尔 h264 硬件加速编码器，视频质量参数为15。你可以更改里面的数值，以达到你期望的画质效果。</p></body>'''
            cursor.execute('''
                            insert into %s 
                            (name, outputOption, description) 
                            values (
                            "%s", 
                            "-c:v hevc_amf -qscale 15 -b:a 256k",
                            '%s'
                            );'''
                           % (presetTableName, presetName, description.replace("'", "''")))

            # h265压制 Nvidia 硬件加速
            presetName = self.tr('H265压制 Nvidia 硬件加速')
            description = '''<body><p>关于使用硬件加速：</p><p>目前硬件加速支持两种编码格式：H264 和 H265</p><p>有3种加速方法，分别对应三家的硬件：Inter、AMD、Nvidia</p><p>不过在苹果电脑上，不管你用的哪家的硬件，都是使用 videotoolbox 编码器。</p><p>需要注意的是，即便你的电脑拥有 Nvidia 显卡，可能也用不了 Nvidia 的硬件加速编码，因为 Nvidia 硬件加速依赖于显卡内部的一种特定的 GPU 的物理部分，专用于编码。只有在 GTX10 和 RTX20 以上的显卡才搭载有这个物理部分。</p><p>使用硬件编码器进行编码，只需要将输出选项中的编码器改成硬件编码器即可，其中：</p><ul><li><code>-c:v h264_qsv</code> 对应 Intel H264 编码</li><li><code>-c:v h264_amf</code> 对应 AMD H264 编码</li><li><code>-c:v h264_nvenc</code> 对应 Nvidia H264 编码</li><li><code>-c:v h264_videotoolbox</code> 对应苹果电脑的 H264 编码</li><li><code>-c:v hevc_qsv</code> 对应 Intel H265 编码</li><li><code>-c:v hevc_amf</code> 对应 AMDH265 编码</li><li><code>-c:v hevc_nvenc</code> 对应 Nvidia H265 编码</li><li><code>-c:v hevc_videotoolbox</code> 对应苹果电脑的 H265 编码</li></ul><p><code>-c:v</code> 表示视频（Video）的编码器（codec）</p><p>在使用硬件加速编码器的时候，控制输出视频的质量是使用 <code>qscale</code> 参数，他的数值可以从 <code>0.1 - 255</code> 不等，数值越小，画质越高，码率越大，输出文件体积越大。同一个数值对于不同的编码器画质的影响效果不同。所以你需要自己测试，在玛律大小和视频画质之间找到一个平衡的 <code>qscale</code> 数值。</p><p>目前所有的硬件加速选项都是类似这样的：<code>-c:v h264_qsv -qscale 15</code> ，这表示使用英特尔 h264 硬件加速编码器，视频质量参数为15。你可以更改里面的数值，以达到你期望的画质效果。</p></body>'''
            cursor.execute('''
                            insert into %s 
                            (name, outputOption, description) 
                            values (
                            "%s", 
                            "-c:v hevc_nvenc -qscale 15 -b:a 256k",
                            '%s'
                            );'''
                           % (presetTableName, presetName, description.replace("'", "''")))

            # h265压制 Mac 硬件加速
            presetName = self.tr('H265压制 Mac 硬件加速')
            description = '''<body><p>关于使用硬件加速：</p><p>目前硬件加速支持两种编码格式：H264 和 H265</p><p>有3种加速方法，分别对应三家的硬件：Inter、AMD、Nvidia</p><p>不过在苹果电脑上，不管你用的哪家的硬件，都是使用 videotoolbox 编码器。</p><p>需要注意的是，即便你的电脑拥有 Nvidia 显卡，可能也用不了 Nvidia 的硬件加速编码，因为 Nvidia 硬件加速依赖于显卡内部的一种特定的 GPU 的物理部分，专用于编码。只有在 GTX10 和 RTX20 以上的显卡才搭载有这个物理部分。</p><p>使用硬件编码器进行编码，只需要将输出选项中的编码器改成硬件编码器即可，其中：</p><ul><li><code>-c:v h264_qsv</code> 对应 Intel H264 编码</li><li><code>-c:v h264_amf</code> 对应 AMD H264 编码</li><li><code>-c:v h264_nvenc</code> 对应 Nvidia H264 编码</li><li><code>-c:v h264_videotoolbox</code> 对应苹果电脑的 H264 编码</li><li><code>-c:v hevc_qsv</code> 对应 Intel H265 编码</li><li><code>-c:v hevc_amf</code> 对应 AMDH265 编码</li><li><code>-c:v hevc_nvenc</code> 对应 Nvidia H265 编码</li><li><code>-c:v hevc_videotoolbox</code> 对应苹果电脑的 H265 编码</li></ul><p><code>-c:v</code> 表示视频（Video）的编码器（codec）</p><p>在使用硬件加速编码器的时候，控制输出视频的质量是使用 <code>qscale</code> 参数，他的数值可以从 <code>0.1 - 255</code> 不等，数值越小，画质越高，码率越大，输出文件体积越大。同一个数值对于不同的编码器画质的影响效果不同。所以你需要自己测试，在玛律大小和视频画质之间找到一个平衡的 <code>qscale</code> 数值。</p><p>目前所有的硬件加速选项都是类似这样的：<code>-c:v h264_qsv -qscale 15</code> ，这表示使用英特尔 h264 硬件加速编码器，视频质量参数为15。你可以更改里面的数值，以达到你期望的画质效果。</p></body>'''
            cursor.execute('''
                                        insert into %s 
                                        (name, outputOption, description) 
                                        values (
                                        "%s", 
                                        "-c:v hevc_videotoolbox -qscale 15 -b:a 256k",
                                        '%s'
                                        );'''
                           % (presetTableName, presetName, description.replace("'", "''")))


            # h264 恒定比特率压制
            presetName = self.tr('H264压制目标比特率6000k')
            description = '''h264恒定比特率压制'''
            cursor.execute('''
                            insert into %s 
                            (name, outputOption, description)
                            values (
                            "%s", 
                            "-b:a 256k -b:v 6000k",
                            '%s'
                            );'''
                           % (presetTableName, presetName, description.replace("'", "''")))

            # h264 恒定比特率二压
            presetName = self.tr('H264 二压 目标比特率2000k')
            description = '''h264恒定比特率二压'''
            extraCode = r"""nullPath = '/dev/null'
connector = '&&'
print(1)
platfm = platform.system()
print(2)
removeCommand = 'rm'
if platfm == 'Windows':
    nullPath = 'NUL'
    removeCommand = 'del'
print(3)
inputOne = self.输入1路径框.text()
inputOneWithoutExt = os.path.splitext(inputOne)[0]
outFile = self.输出路径框.text()
outFileWithoutExt = os.path.splitext(outFile)[0]
logFileName = outFileWithoutExt + r'-0.log'
print(logFileName)
if platfm == 'Windows':
    logFileName = logFileName.replace('/', '\\')
logTreeFileName = outFileWithoutExt + r'-0.log.mbtree'
if platfm == 'Windows':
    logTreeFileName = logTreeFileName.replace('/', '\\')
tempCommand = self.finalCommand.replace('"' + outFile + '"', r'-passlogfile "%s"' % (outFileWithoutExt) + ' "' + outFile + '"')
self.finalCommand = r'''ffmpeg -y -hide_banner -i "%s" -passlogfile "%s"  -c:v libx264 -pass 1 -an -f rawvideo "%s" %s %s %s %s "%s" %s %s "%s"''' % (inputOne, outFileWithoutExt, nullPath, connector, tempCommand, connector, removeCommand, logFileName, connector, removeCommand,logTreeFileName)
"""
            extraCode = extraCode.replace("'", "''")
            cursor.execute('''
                            insert into %s 
                            (name, outputOption, extraCode, description)
                            values (
                            "%s", 
                            "-c:v libx264 -pass 2 -b:v 2000k -preset slow -b:a 256k", 
                            '%s',
                            '%s'
                            );''' % (presetTableName, presetName, extraCode, description.replace("'", "''")))

            # 复制视频流到mp4容器
            presetName = self.tr('复制视频流到mp4容器')
            cursor.execute('''
                            insert into %s
                            (name, outputExt, outputOption)
                            values (
                            '%s', 
                            'mp4', 
                            '-c:v copy -b:a 256k'
                            );''' % (presetTableName, presetName))

            # 将输入文件打包到mkv格式容器
            presetName = self.tr('将输入文件打包到mkv格式容器')
            cursor.execute('''
                            insert into %s
                            (name, outputExt, outputOption)
                            values (
                            '%s', 
                            'mkv', 
                            '-c copy'
                            );'''
                           % (presetTableName, presetName))

            # 转码到mp3格式
            presetName = self.tr('转码到mp3格式')
            cursor.execute('''
                            insert into %s
                            (name, outputExt, outputOption)
                            values (
                            '%s', 
                            'mp3', 
                            '-vn -b:a 256k'
                            );''' % (presetTableName, presetName))

            # GIF (15fps 480p)
            presetName = self.tr('GIF (15fps 480p)')
            description = '''GIF (15fps 480p)'''
            cursor.execute('''
                            insert into %s 
                            (name, outputExt, outputOption, description)
                            values (
                            '%s', 
                            'gif', 
                            '-filter_complex "[0:v] scale=480:-1, fps=15, split [a][b];[a] palettegen [p];[b][p] paletteuse"',
                            '%s'
                            );''' % (presetTableName, presetName, description.replace("'", "''")))

            # 区域模糊
            presetName = self.tr('区域模糊')
            outputOption = '''-vf "split [main][tmp]; [tmp] crop=宽:高:X轴位置:Y轴位置, boxblur=luma_radius=25:luma_power=2:enable='between(t,第几秒开始,第几秒结束)'[tmp]; [main][tmp] overlay=X轴位置:Y轴位置"'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 视频两倍速
            presetName = self.tr('视频两倍速')
            outputOption = '''-filter_complex "[0:v]setpts=1/2*PTS[v];[0:a]atempo=2 [a]" -map "[v]" -map "[a]" '''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 音频两倍速
            presetName = self.tr('音频两倍速')
            outputOption = '''-filter_complex "[0:a]atempo=2.0[a]" -map "[a]"'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 视频0.5倍速 + 光流法补帧到60帧
            presetName = self.tr('视频0.5倍速 + 光流法补帧到60帧')
            outputOption = '''-filter_complex "[0:v]setpts=2*PTS[v];[0:a]atempo=1/2 [a];[v]minterpolate='mi_mode=mci:mc_mode=aobmc:me_mode=bidir:mb_size=16:vsbmc=1:fps=60'[v]" -map "[v]" -map "[a]" -max_muxing_queue_size 1024'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 光流法补帧到60帧
            presetName = self.tr('光流法补帧到60帧')
            outputOption = '''-filter_complex "[0:v]scale=-2:-2[v];[v]minterpolate='mi_mode=mci:mc_mode=aobmc:me_mode=bidir:mb_size=16:vsbmc=1:fps=60'" -max_muxing_queue_size 1024'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 视频倒放
            presetName = self.tr('视频倒放')
            outputOption = '''-vf reverse -af areverse'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 音频倒放
            presetName = self.tr('音频倒放')
            outputOption = '''-af areverse'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 设置画面比例
            presetName = self.tr('设置画面比例')
            outputOption = '''-aspect:0 16:9'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 视频流时间戳偏移，用于同步音画
            presetName = self.tr('视频流时间戳偏移，用于同步音画')
            inputOneOption = '''-itsoffset 1'''
            inputOneOption = inputOneOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, inputOneOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, inputOneOption))

            # 从视频区间每秒提取n张照片
            presetName = self.tr('从视频区间每秒提取n张照片')
            outputOption = ''' -r 1 -q:v 2 -f image2 -tatget pal-dvcd-r'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputExt, outputOption)
                            values (
                            '%s', 
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, r'%03d.jpg', outputOption))

            # 截取指定数量的帧保存为图片
            presetName = self.tr('截取指定数量的帧保存为图片')
            outputOption = '''-vframes 5'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputExt, outputOption)
                            values (
                            '%s', 
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, r'%03d.jpg', outputOption))

            # 一图流
            presetName = self.tr('一图流')
            outputOption = '''-c:v libx264 -tune stillimage -c:a aac -shortest'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, inputOneOption, outputOption)
                            values (
                            '%s', 
                            '-loop 1', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 裁切视频画面
            presetName = self.tr('裁切视频画面')
            outputOption = '''-strict -2 -vf crop=w:h:x:y'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 视频旋转度数
            presetName = self.tr('视频旋转度数')
            outputOption = '''-c copy -metadata:s:v:0 rotate=90'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 水平翻转画面
            presetName = self.tr('水平翻转画面')
            outputOption = '''-vf "hflip" '''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 垂直翻转画面
            presetName = self.tr('垂直翻转画面')
            outputOption = '''-vf "vflip" '''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 设定至指定分辨率，并且自动填充黑边
            presetName = self.tr('设定至指定分辨率，并且自动填充黑边')
            outputOption = '''-vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black" '''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 视频或音乐添加封面图片
            presetName = self.tr('视频或音乐添加封面图片')
            outputOption = '''-map 0 -map 1 -c copy -c:v:1 jpg -disposition:v:1 attached_pic'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 声音响度标准化
            presetName = self.tr('声音响度标准化')
            outputOption = '''-af "loudnorm=i=-24.0:lra=7.0:tp=-2.0:" -c:v copy'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 音量大小调节
            presetName = self.tr('音量大小调节')
            outputOption = '''-af "volume=1.0"'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 静音第一个声道
            presetName = self.tr('静音第一个声道')
            outputOption = '''-map_channel -1 -map_channel 0.0.1 '''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 静音所有声道
            presetName = self.tr('静音所有声道')
            outputOption = '''-map_channel [-1]"'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 交换左右声道
            presetName = self.tr('交换左右声道')
            outputOption = '''-map_channel 0.0.1 -map_channel 0.0.0 '''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

            # 两个音频流混合到一个文件
            presetName = self.tr('两个音频流混合到一个文件')
            outputOption = '''-filter_complex "[0:1] [1:1] amerge" -c:v copy'''
            outputOption = outputOption.replace("'", "''")
            cursor.execute('''
                            insert into %s
                            (name, outputOption)
                            values (
                            '%s', 
                            '%s'
                            );''' % (presetTableName, presetName, outputOption))

        else:
            print('存储"预设"的表单已存在')
        conn.commit()
        # 不在这里关数据库了()
        return True

    # 将数据库的预设填入列表（更新列表）
    def refreshList(self):
        ########改用主数据库
        cursor = conn.cursor()
        presetData = cursor.execute(
            'select id, name, inputOneOption, inputTwoOption, outputExt, outputOption, extraCode from %s order by id' % (
                presetTableName))
        self.预设列表.clear()
        for i in presetData:
            self.预设列表.addItem(i[1])
        # 不在这里关数据库了()
        pass

    # 选择一个预设时，将预设中的命令填入相应的框
    def presetItemSelected(self, Index):
        if self.commandOptionsChanged == True:
            result = QMessageBox.question(self, '覆盖命令选项', '命令选项已经被手工修改过，使用预设会覆盖掉已修改的选项，确认要继续吗？', QMessageBox.Yes | QMessageBox.No)
            if result == QMessageBox.No:
                return
        global 当前已选择的条目
        当前已选择的条目 = self.预设列表.item(self.预设列表.row(Index)).text()
        # print(当前已选择的条目)
        presetData = conn.cursor().execute(
            'select id, name, inputOneOption, inputTwoOption, outputExt, outputOption, extraCode, description from %s where name = "%s"' % (
                presetTableName, 当前已选择的条目)).fetchone()
        self.inputOneOption = presetData[2]
        self.inputTwoOption = presetData[3]
        self.outputExt = presetData[4]
        # print(presetData[4])
        self.outputOption = presetData[5]
        self.extraCode = presetData[6]
        self.description = presetData[7]
        if self.inputOneOption != None:
            self.输入1选项输入框.setText(self.inputOneOption)
        else:
            self.输入1选项输入框.clear()

        if self.inputTwoOption != None:
            self.输入2选项输入框.setText(self.inputTwoOption)
        else:
            self.输入2选项输入框.clear()

        if self.outputExt != None and self.outputExt != '':
            原来的输出路径 = self.输出路径框.text()
            if '.' in self.outputExt:
                修改后缀名后的输出路径 = re.sub('\..+?$', self.outputExt, 原来的输出路径)
            else:
                修改后缀名后的输出路径 = re.sub('(?<=\.).+?$', self.outputExt, 原来的输出路径)
            if 修改后缀名后的输出路径 != '':
                self.输出路径框.setText(修改后缀名后的输出路径)
            pass

        if self.outputOption != None:
            self.输出选项输入框.setPlainText(self.outputOption)
        else:
            self.输出选项输入框.clear()
        self.commandOptionsChanged = False

    # 点击添加一个预设
    def addPresetButtonClicked(self):
        dialog = self.SetupPresetItemDialog()

    # 点击删除按钮后删除预设
    def delPresetButtonClicked(self):
        global 当前已选择的条目
        try:
            当前已选择的条目
            answer = QMessageBox.question(self, self.tr('删除预设'), self.tr('将要删除“%s”预设，是否确认？') % (当前已选择的条目))
            if answer == QMessageBox.Yes:
                id = conn.cursor().execute(
                    '''select id from %s where name = '%s'; ''' % (presetTableName, 当前已选择的条目)).fetchone()[0]
                conn.cursor().execute("delete from %s where id = '%s'; " % (presetTableName, id))
                conn.cursor().execute("update %s set id=id-1 where id > %s" % (presetTableName, id))
                conn.commit()
                self.refreshList()
        except:
            QMessageBox.information(self, self.tr('删除失败'), self.tr('还没有选择要删除的预设'))

    # 向上移动预设
    def upwardButtonClicked(self):
        currentRow = self.预设列表.currentRow()
        if currentRow > 0:
            currentText = self.预设列表.currentItem().text()
            currentText = currentText.replace("'", "''")
            id = conn.cursor().execute(
                "select id from %s where name = '%s'" % (presetTableName, currentText)).fetchone()[0]
            conn.cursor().execute("update %s set id=10000 where id=%s-1 " % (presetTableName, id))
            conn.cursor().execute("update %s set id = id - 1 where name = '%s'" % (presetTableName, currentText))
            conn.cursor().execute("update %s set id=%s where id=10000 " % (presetTableName, id))
            conn.commit()
            self.refreshList()
            self.预设列表.setCurrentRow(currentRow - 1)

    # 向下移动预设
    def downwardButtonClicked(self):
        currentRow = self.预设列表.currentRow()
        totalRow = self.预设列表.count()
        if currentRow > -1 and currentRow < totalRow - 1:
            currentText = self.预设列表.currentItem().text()
            currentText = currentText.replace("'", "''")
            id = conn.cursor().execute(
                "select id from %s where name = '%s'" % (presetTableName, currentText)).fetchone()[0]
            conn.cursor().execute("update %s set id=10000 where id=%s+1 " % (presetTableName, id))
            conn.cursor().execute("update %s set id = id + 1 where name = '%s'" % (presetTableName, currentText))
            conn.cursor().execute("update %s set id=%s where id=10000 " % (presetTableName, id))
            conn.commit()
            self.refreshList()
            if currentRow < totalRow:
                self.预设列表.setCurrentRow(currentRow + 1)
            else:
                self.预设列表.setCurrentRow(currentRow)
        return

    # 看预设描述
    def checkPresetHelpButtonClicked(self):
        if self.预设列表.currentRow() > -1:
            dialog = QDialog()
            dialog.setWindowTitle(self.tr('预设描述'))
            dialog.resize(1000, 800)
            textEdit = QTextEdit()
            font = QFont()
            layout = QHBoxLayout()
            layout.addWidget(textEdit)
            dialog.setLayout(layout)
            content = conn.cursor().execute("select description from %s where name = '%s'" % (
                presetTableName, self.预设列表.currentItem().text())).fetchone()[0]
            textEdit.setHtml(content)
            font.setPointSize(13)
            textEdit.setFont(font)
            print(True)
            dialog.exec()

    # 添加预设对话框
    class SetupPresetItemDialog(QDialog):
        def __init__(self):
            super().__init__()
            self.initUI()

        def initUI(self):
            self.setWindowTitle(self.tr('添加或更新预设'))
            ########改用主数据库

            # 预设名称
            if True:
                self.预设名称标签 = QLabel(self.tr('预设名称：'))
                self.预设名称输入框 = QLineEdit()
                self.预设名称输入框.textChanged.connect(self.presetNameEditChanged)

            # 输入1选项
            if True:
                self.输入1选项标签 = QLabel(self.tr('输入1选项：'))
                self.输入1选项输入框 = QLineEdit()

            # 输入2选项
            if True:
                self.输入2选项标签 = QLabel(self.tr('输入2选项：'))
                self.输入2选项输入框 = QLineEdit()

            # 输出选项
            if True:
                # 输出后缀名
                if True:
                    self.输出后缀标签 = QLabel(self.tr('输出后缀名：'))
                    self.输出后缀输入框 = QLineEdit()
                # 输出选项
                if True:
                    self.输出选项标签 = QLabel(self.tr('输出选项：'))
                    self.输出选项输入框 = QPlainTextEdit()
                    self.输出选项输入框.setMaximumHeight(70)

            # 额外代码
            if True:
                self.额外代码标签 = QLabel(self.tr('额外代码：'))
                self.额外代码输入框 = QPlainTextEdit()
                self.额外代码输入框.setMaximumHeight(70)
                self.额外代码输入框.setPlaceholderText(self.tr('这里是用于实现一些比较复杂的预设的，普通用户不用管这个框'))

            # 描述
            if True:
                self.描述标签 = QLabel(self.tr('描述：'))
                self.描述输入框 = QTextEdit()

            # 底部按钮
            if True:
                self.submitButton = QPushButton(self.tr('确定'))
                self.submitButton.clicked.connect(self.submitButtonClicked)
                self.cancelButton = QPushButton(self.tr('取消'))
                self.cancelButton.clicked.connect(lambda: self.close())

            # 各个区域组装起来
            if True:
                self.表格布局控件 = QWidget()
                self.表格布局 = QFormLayout()
                self.表格布局.addRow(self.预设名称标签, self.预设名称输入框)
                self.表格布局.addRow(self.输入1选项标签, self.输入1选项输入框)
                self.表格布局.addRow(self.输入2选项标签, self.输入2选项输入框)
                self.表格布局.addRow(self.输出后缀标签, self.输出后缀输入框)
                self.表格布局.addRow(self.输出选项标签, self.输出选项输入框)
                self.表格布局.addRow(self.额外代码标签, self.额外代码输入框)
                self.表格布局.addRow(self.描述标签, self.描述输入框)
                self.表格布局控件.setLayout(self.表格布局)

                self.按钮布局控件 = QWidget()
                self.按钮布局 = QHBoxLayout()

                self.按钮布局.addWidget(self.submitButton)

                self.按钮布局.addWidget(self.cancelButton)

                self.按钮布局控件.setLayout(self.按钮布局)

                self.主布局vbox = QVBoxLayout()
                self.主布局vbox.addWidget(self.表格布局控件)
                self.主布局vbox.addWidget(self.按钮布局控件)
            self.setLayout(self.主布局vbox)
            # self.submitButton.setFocus()

            # 查询数据库，填入输入框
            if True:
                global 当前已选择的条目
                try:
                    当前已选择的条目
                except:
                    当前已选择的条目 = None
                if 当前已选择的条目 != None:
                    presetData = conn.cursor().execute(
                        'select id, name, inputOneOption, inputTwoOption, outputExt, outputOption, extraCode, description from %s where name = "%s"' % (
                            presetTableName, 当前已选择的条目)).fetchone()
                    if presetData != None:
                        self.inputOneOption = presetData[2]
                        self.inputTwoOption = presetData[3]
                        self.outputExt = presetData[4]
                        self.outputOption = presetData[5]
                        self.extraCode = presetData[6]
                        self.description = presetData[7]

                        self.预设名称输入框.setText(当前已选择的条目)
                        if self.inputOneOption != None:
                            self.输入1选项输入框.setText(self.inputOneOption)
                        if self.inputTwoOption != None:
                            self.输入2选项输入框.setText(self.inputTwoOption)
                        if self.outputExt != None:
                            self.输出后缀输入框.setText(self.outputExt)
                        if self.outputOption != None:
                            self.输出选项输入框.setPlainText(self.outputOption)
                        if self.extraCode != None:
                            self.额外代码输入框.setPlainText(self.extraCode)
                        if self.description != None:
                            self.描述输入框.setHtml(self.description)

            # 根据刚开始预设名字是否为空，设置确定键可否使用
            if True:
                self.新预设名称 = self.预设名称输入框.text()
                if self.新预设名称 == '':
                    self.submitButton.setEnabled(False)

            self.exec()

        # 根据刚开始预设名字是否为空，设置确定键可否使用
        def presetNameEditChanged(self):
            self.新预设名称 = self.预设名称输入框.text()
            if self.新预设名称 == '':
                if self.submitButton.isEnabled():
                    self.submitButton.setEnabled(False)
            else:
                if not self.submitButton.isEnabled():
                    self.submitButton.setEnabled(True)

        # 点击提交按钮后, 添加预设
        def submitButtonClicked(self):
            self.新预设名称 = self.预设名称输入框.text()
            self.新预设名称 = self.新预设名称.replace("'", "''")

            self.新预设输入1选项 = self.输入1选项输入框.text()
            self.新预设输入1选项 = self.新预设输入1选项.replace("'", "''")

            self.新预设输入2选项 = self.输入2选项输入框.text()
            self.新预设输入2选项 = self.新预设输入2选项.replace("'", "''")

            self.新预设输出后缀 = self.输出后缀输入框.text()
            self.新预设输出后缀 = self.新预设输出后缀.replace("'", "''")

            self.新预设输出选项 = self.输出选项输入框.toPlainText()
            self.新预设输出选项 = self.新预设输出选项.replace("'", "''")

            self.新预设额外代码 = self.额外代码输入框.toPlainText()
            self.新预设额外代码 = self.新预设额外代码.replace("'", "''")

            self.新预设描述 = self.描述输入框.toHtml()
            self.新预设描述 = self.新预设描述.replace("'", "''")

            result = conn.cursor().execute(
                'select name from %s where name = "%s";' % (presetTableName, self.新预设名称)).fetchone()
            if result == None:
                try:
                    maxIdItem = conn.cursor().execute(
                        'select id from %s order by id desc' % presetTableName).fetchone()
                    if maxIdItem != None:
                        maxId = maxIdItem[0]
                    else:
                        maxId = 0
                    conn.cursor().execute(
                        '''insert into %s (id, name, inputOneOption, inputTwoOption, outputExt, outputOption, extraCode, description) values (%s, '%s', '%s', '%s', '%s', '%s', '%s', '%s');''' % (
                            presetTableName, maxId + 1, self.新预设名称, self.新预设输入1选项, self.新预设输入2选项, self.新预设输出后缀,
                            self.新预设输出选项,
                            self.新预设额外代码, self.新预设描述))
                    conn.commit()
                    QMessageBox.information(self, self.tr('添加预设'), self.tr('新预设添加成功'))
                    self.close()
                except:
                    QMessageBox.warning(self, self.tr('添加预设'), self.tr('新预设添加失败，你可以把失败过程重新操作记录一遍，然后发给作者'))
            else:
                answer = QMessageBox.question(self, self.tr('覆盖预设'), self.tr('''已经存在名字相同的预设，你可以选择换一个预设名字或者覆盖旧的预设。是否要覆盖？'''))
                if answer == QMessageBox.Yes:  # 如果同意覆盖
                    try:
                        conn.cursor().execute(
                            '''update %s set name = '%s', inputOneOption = '%s', inputTwoOption = '%s', outputExt = '%s', outputOption = '%s', extraCode = '%s', description = '%s' where name = '%s';''' % (
                                presetTableName, self.新预设名称, self.新预设输入1选项, self.新预设输入2选项, self.新预设输出后缀, self.新预设输出选项,
                                self.新预设额外代码, self.新预设描述, self.新预设名称))
                        # print(
                        #     '''update %s set name = '%s', inputOneOption = '%s', inputTwoOption = '%s', outputExt = '%s', outputOption = '%s', extraCode = '%s', description = '%s' where name = '%s';''' % (
                        #         presetTableName, self.新预设名称, self.新预设输入1选项, self.新预设输入2选项, self.新预设输出后缀, self.新预设输出选项,
                        #         self.新预设额外代码, self.新预设描述, self.新预设名称))
                        conn.commit()
                        QMessageBox.information(self, self.tr('更新预设'), self.tr('预设更新成功'))
                        self.close()
                    except:
                        QMessageBox.warning(self, self.tr('更新预设'), self.tr('预设更新失败，你可以把失败过程重新操作记录一遍，然后发给作者'))

        def closeEvent(self, a0: QCloseEvent) -> None:
            try:
                # 不在这里关数据库了()
                mainWindow.ffmpegMainTab.refreshList()
            except:
                pass

    # 点击会变化“截取时长”、 “截止时刻”的label
    class ClickableEndTimeLable(QLabel):
        def __init__(self):
            super().__init__()
            self.setText(self.tr('截取时长：'))

        def enterEvent(self, *args, **kwargs):
            mainWindow.status.showMessage(self.tr('点击交换“截取时长”和“截止时刻”'))

        def leaveEvent(self, *args, **kwargs):
            mainWindow.status.showMessage('')

        def mousePressEvent(self, QMouseEvent):
            # print(self.text())
            if self.text() == self.tr('截取时长：'):
                self.setText(self.tr('截止时刻：'))
            else:
                self.setText(self.tr('截取时长：'))
            mainWindow.ffmpegMainTab.generateFinalCommand()

    # 点击会交换横竖分辨率的 label
    class ClickableResolutionTimesLable(QLabel):
        def __init__(self):
            # global main
            super().__init__()
            self.setText('×')
            self.setToolTip(self.tr('点击交换横纵分辨率'))
            # mainWindow.status.showMessage('1')

        def enterEvent(self, *args, **kwargs):
            mainWindow.status.showMessage(self.tr('点击交换横竖分辨率'))

        def leaveEvent(self, *args, **kwargs):
            mainWindow.status.showMessage('')

        def mousePressEvent(self, QMouseEvent):
            x = mainWindow.ffmpegMainTab.X轴分辨率输入框.text()
            mainWindow.ffmpegMainTab.X轴分辨率输入框.setText(mainWindow.ffmpegMainTab.Y轴分辨率输入框.text())
            mainWindow.ffmpegMainTab.Y轴分辨率输入框.setText(x)

    # 分辨率预设 dialog
    class ResolutionDialog(QDialog):
        def __init__(self):
            super().__init__()
            self.resolutions = ['4096 x 2160 (Ultra HD 4k)', '2560 x 1440 (Quad HD 2k)', '1920 x 1080 (Full HD 1080p)',
                                '1280 x 720 (HD 720p)', '720 x 480 (480p)', '480 x 360 (360p)']
            self.setWindowTitle(self.tr('选择分辨率预设'))
            self.listWidget = QListWidget()
            self.listWidget.addItems(self.resolutions)
            self.listWidget.itemDoubleClicked.connect(self.setResolution)
            self.layout = QVBoxLayout()
            self.layout.addWidget(self.listWidget)
            self.setLayout(self.layout)
            self.exec()

        def setResolution(self):
            resolution = re.findall('\d+', self.listWidget.currentItem().text())
            mainWindow.ffmpegMainTab.X轴分辨率输入框.setText(resolution[0])
            mainWindow.ffmpegMainTab.Y轴分辨率输入框.setText(resolution[1])
            self.close()

    # 剪切时间的提示 QLineEdit
    class CutTimeEdit(QLineEdit):
        def __init__(self):
            super().__init__()
            self.setAlignment(Qt.AlignCenter)

        def enterEvent(self, *args, **kwargs):
            mainWindow.status.showMessage(self.tr('例如 “00:05.00”、“23.189”、“12:03:45”的形式都是有效的，注意冒号是英文冒号'))

        def leaveEvent(self, *args, **kwargs):
            mainWindow.status.showMessage('')

    # 分辨率的提示 QLineEdit
    class ResolutionEdit(QLineEdit):
        def __init__(self):
            super().__init__()
            self.setAlignment(Qt.AlignCenter)

        def enterEvent(self, *args, **kwargs):
            mainWindow.status.showMessage(self.tr('负数表示自适应。例如，“ 720 × -2 ” 表示横轴分辨率为 720，纵轴分辨率为自适应且能够整除 -2'))

        def leaveEvent(self, *args, **kwargs):
            mainWindow.status.showMessage('')

# 分割视频
class FFmpegSplitVideoTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initGui()

    def initGui(self):
        self.masterLayout = QVBoxLayout()


        # self.masterLayout.addStretch(0)

        self.setLayout(self.masterLayout)

        # 输出文件选项
        if True:
            self.ffmpegOutputOptionGroup = QGroupBox(self.tr('总选项'))
            self.masterLayout.addWidget(self.ffmpegOutputOptionGroup)
            self.ffmpegOutputOptionLayout = QGridLayout()
            self.ffmpegOutputOptionGroup.setLayout(self.ffmpegOutputOptionLayout)
            self.ffmpegOutputOptionHint = HintLabel(self.tr('输出文件选项(默认可为空，但可选硬件加速)：'))
            self.ffmpegOutputOptionHint.hint = self.tr('在这里可以选择对应你设备的硬件加速编码器，Intel 对应 qsv，AMD 对应 amf，Nvidia 对应 nvenc, 苹果电脑对应 videotoolbox')
            self.ffmpegOutputOptionBox = HintCombobox()
            self.ffmpegOutputOptionBox.hint = self.tr('在这里可以选择对应你设备的硬件加速编码器，Intel 对应 qsv，AMD 对应 amf，Nvidia 对应 nvenc, 苹果电脑对应 videotoolbox')
            self.ffmpegOutputOptionBox.setEditable(True)
            self.ffmpegOutputOptionBox.addItem('')
            self.ffmpegOutputOptionBox.addItem('-c:v h264_qsv -qscale 15')
            self.ffmpegOutputOptionBox.addItem('-c:v h264_amf -qscale 15')
            self.ffmpegOutputOptionBox.addItem('-c:v h264_nvenc -qscale 15')
            self.ffmpegOutputOptionBox.addItem('-c:v h264_videotoolbox -qscale 15')
            self.ffmpegOutputOptionBox.addItem('-c:v hevc_qsv -qscale 15')
            self.ffmpegOutputOptionBox.addItem('-c:v hevc_amf -qscale 15')
            self.ffmpegOutputOptionBox.addItem('-c:v hevc_nvenc -qscale 15')
            self.ffmpegOutputOptionBox.addItem('-c:v hevc_videotoolbox -qscale 15')
            self.ffmpegOutputOptionLayout.addWidget(self.ffmpegOutputOptionHint, 0, 0, 1, 1)
            self.ffmpegOutputOptionLayout.addWidget(self.ffmpegOutputOptionBox, 0, 1, 1, 2)

        self.masterLayout.addSpacing(5)

        # 根据字幕分割片段
        if True:
            self.subtitleSplitVideoGroup = QGroupBox(self.tr('对字幕中的每一句剪出对应的视频片段'))
            self.subtitleSplitVideoLayout = QVBoxLayout()
            self.subtitleSplitVideoGroup.setLayout(self.subtitleSplitVideoLayout)
            self.masterLayout.addWidget(self.subtitleSplitVideoGroup)

            self.subtitleSplitInputHint = QLabel(self.tr('输入视频：'))
            self.subtitleSplitInputBox = MyQLine()
            self.subtitleSplitInputBox.textChanged.connect(self.setSubtitleSplitOutputFolder)
            self.subtitleSplitInputButton = QPushButton(self.tr('选择文件'))
            self.subtitleSplitInputButton.clicked.connect(self.subtitleSplitInputButtonClicked)

            self.subtitleHint = QLabel(self.tr('输入字幕：'))
            self.subtitleSplitSubtitleFileInputBox = MyQLine()
            self.subtitleSplitSubtitleFileInputBox.setPlaceholderText(self.tr('支持 srt、ass、vtt 字幕，或者内置字幕的 mkv'))
            self.subtitleButton = QPushButton(self.tr('选择文件'))
            self.subtitleButton.clicked.connect(self.subtitleSplitSubtitleFileInputButtonClicked)

            self.outputHint = QLabel(self.tr('输出文件夹：'))
            self.subtitleSplitOutputBox = QLineEdit()
            self.subtitleSplitOutputBox.setReadOnly(True)

            self.subtitleSplitSwitch = QCheckBox(self.tr('指定时间段'))
            self.subtitleSplitStartTimeHint = QLabel(self.tr('起始时刻：'))
            self.subtitleSplitStartTimeHint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.subtitleSplitStartTimeBox = QLineEdit()
            self.subtitleSplitStartTimeBox.setAlignment(Qt.AlignCenter)
            self.subtitleSplitEndTimeHint = QLabel(self.tr('截止时刻：'))
            self.subtitleSplitEndTimeHint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.subtitleSplitEndTimeBox = QLineEdit()
            self.subtitleSplitEndTimeBox.setAlignment(Qt.AlignCenter)

            self.timeValidator = QRegExpValidator(self)
            self.timeValidator.setRegExp(QRegExp(r'[0-9]{0,2}:?[0-9]{0,2}:?[0-9]{0,2}\.?[0-9]{0,2}'))
            self.subtitleSplitStartTimeBox.setValidator(self.timeValidator)
            self.subtitleSplitEndTimeBox.setValidator(self.timeValidator)

            self.subtitleSplitStartTimeHint.hide()
            self.subtitleSplitStartTimeBox.hide()
            self.subtitleSplitEndTimeHint.hide()
            self.subtitleSplitEndTimeBox.hide()
            self.subtitleSplitSwitch.clicked.connect(self.onSubtitleSplitSwitchClicked)

            self.subtitleOffsetHint = QLabel(self.tr('字幕时间偏移：'))
            self.subtitleOffsetBox = QDoubleSpinBox()
            self.subtitleOffsetBox.setAlignment(Qt.AlignCenter)
            self.subtitleOffsetBox.setDecimals(2)
            self.subtitleOffsetBox.setValue(0)
            self.subtitleOffsetBox.setMinimum(-100)
            self.subtitleOffsetBox.setSingleStep(0.1)

            self.exportClipSubtitleSwitch = QCheckBox(self.tr('同时导出分段srt字幕'))
            self.exportClipSubtitleSwitch.setChecked(True)

            self.subtitleNumberPerClipHint = QLabel(self.tr('每多少句剪为一段：'))
            self.subtitleNumberPerClipHint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.subtitleNumberPerClipBox = QSpinBox()
            self.subtitleNumberPerClipBox.setValue(1)
            self.subtitleNumberPerClipBox.setAlignment(Qt.AlignCenter)
            self.subtitleNumberPerClipBox.setMinimum(1)

            self.subtitleSplitButton = QPushButton(self.tr('运行'))
            self.subtitleSplitButton.clicked.connect(self.onSubtitleSplitRunButtonClicked)
            self.subtitleSplitButton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

            self.subtitleSplitVideoInputWidgetLayout = QHBoxLayout()  # 输入文件
            self.subtitleSplitVideoInputWidgetLayout.addWidget(self.subtitleSplitInputBox, 2)
            self.subtitleSplitVideoInputWidgetLayout.addWidget(self.subtitleSplitInputButton, 1)
            self.subtitleSplitVideoInputWidgetLayout.setContentsMargins(0, 0, 0, 0)
            self.subtitleSplitVideoInputWidget = QWidget()
            self.subtitleSplitVideoInputWidget.setLayout(self.subtitleSplitVideoInputWidgetLayout)
            self.subtitleSplitVideoInputWidget.setContentsMargins(0, 0, 0, 0)

            self.subtitleSplitVideoSubtitleFileWidgetLayout = QHBoxLayout()  # 输入字幕
            self.subtitleSplitVideoSubtitleFileWidgetLayout.addWidget(self.subtitleSplitSubtitleFileInputBox, 2)
            self.subtitleSplitVideoSubtitleFileWidgetLayout.addWidget(self.subtitleButton, 1)
            self.subtitleSplitVideoSubtitleFileWidgetLayout.setContentsMargins(0, 0, 0, 0)
            self.subtitleSplitVideoSubtitleFileWidget = QWidget()
            self.subtitleSplitVideoSubtitleFileWidget.setLayout(self.subtitleSplitVideoSubtitleFileWidgetLayout)
            self.subtitleSplitVideoSubtitleFileWidget.setContentsMargins(0, 0, 0, 0)

            self.subtitleSplitVideoStartEndTimeWidgetLayout = QHBoxLayout()  # 起始和终止时间
            self.subtitleSplitVideoStartEndTimeWidgetLayout.addWidget(self.subtitleSplitStartTimeHint, 1)
            self.subtitleSplitVideoStartEndTimeWidgetLayout.addWidget(self.subtitleSplitStartTimeBox, 1)
            self.subtitleSplitVideoStartEndTimeWidgetLayout.addSpacing(50)
            self.subtitleSplitVideoStartEndTimeWidgetLayout.addWidget(self.subtitleSplitEndTimeHint, 1)
            self.subtitleSplitVideoStartEndTimeWidgetLayout.addWidget(self.subtitleSplitEndTimeBox, 1)
            self.subtitleSplitVideoStartEndTimeWidgetLayout.setContentsMargins(0, 0, 0, 0)
            self.subtitleSplitVideoStartEndTimeWidget = QWidget()
            self.subtitleSplitVideoStartEndTimeWidget.setLayout(self.subtitleSplitVideoStartEndTimeWidgetLayout)
            self.subtitleSplitVideoStartEndTimeWidget.setContentsMargins(0, 0, 0, 0)

            self.subtitleSplitVideoCentenceOptionWidgetLayout = QHBoxLayout()  # 指定时间段
            self.subtitleSplitVideoCentenceOptionWidgetLayout.addWidget(self.exportClipSubtitleSwitch, 1)
            self.subtitleSplitVideoCentenceOptionWidgetLayout.addWidget(self.subtitleNumberPerClipHint, 1)
            self.subtitleSplitVideoCentenceOptionWidgetLayout.addWidget(self.subtitleNumberPerClipBox, 1)
            self.subtitleSplitVideoCentenceOptionWidgetLayout.setContentsMargins(0, 0, 0, 0)
            self.subtitleSplitVideoCentenceOptionWidget = QWidget()
            self.subtitleSplitVideoCentenceOptionWidget.setLayout(self.subtitleSplitVideoCentenceOptionWidgetLayout)
            self.subtitleSplitVideoCentenceOptionWidget.setContentsMargins(0, 0, 0, 0)

            self.subtitleSplitVdeoFormLayout = QFormLayout()
            self.subtitleSplitVdeoFormLayout.addRow(self.subtitleSplitInputHint, self.subtitleSplitVideoInputWidget) # 输入文件
            self.subtitleSplitVdeoFormLayout.addRow(self.subtitleHint, self.subtitleSplitVideoSubtitleFileWidget) # 输入字幕
            self.subtitleSplitVdeoFormLayout.addRow(self.outputHint, self.subtitleSplitOutputBox) # 输出文件
            self.subtitleSplitVdeoFormLayout.addRow(self.subtitleSplitSwitch, self.subtitleSplitVideoStartEndTimeWidget) # 起始和终止时间
            self.subtitleSplitVdeoFormLayout.addRow(self.subtitleOffsetHint, self.subtitleOffsetBox) # 起始和终止时间
            self.subtitleSplitVdeoFormLayout.setWidget(5, QFormLayout.SpanningRole, self.subtitleSplitVideoCentenceOptionWidget) # 多少句为一段


            self.subtitleSplitVdeoHboxLayout = QHBoxLayout()
            self.subtitleSplitVdeoHboxLayout.setContentsMargins(0, 0, 0, 0)
            self.subtitleSplitVdeoHboxLayout.addLayout(self.subtitleSplitVdeoFormLayout, 3)
            self.subtitleSplitVdeoHboxLayout.addWidget(self.subtitleSplitButton, 0)

            self.subtitleSplitVideoLayout.addLayout(self.subtitleSplitVdeoHboxLayout)  # 在主垂直布局添加选项的表单布局
            self.subtitleSplitVideoLayout.addStretch(1)



        self.masterLayout.addSpacing(5)

        # 根据时长分割片段
        if True:
            self.durationSplitVideoGroup = QGroupBox(self.tr('根据指定时长分割片段'))
            self.durationSplitVideoLayout = QVBoxLayout()
            self.durationSplitVideoGroup.setLayout(self.durationSplitVideoLayout)
            self.masterLayout.addWidget(self.durationSplitVideoGroup)

            self.durationSplitVideoInputHint = QLabel(self.tr('输入路径：'))
            self.durationSplitVideoInputBox = MyQLine()
            self.durationSplitVideoInputBox.textChanged.connect(self.setSubtitleSplitOutputFolder)
            self.durationSplitVideoInputButton = QPushButton(self.tr('选择文件'))

            self.durationSplitVideoOutputHint = QLabel(self.tr('输出文件夹：'))
            self.durationSplitVideoOutputBox = QLineEdit()
            self.durationSplitVideoOutputBox.setReadOnly(True)



            self.durationSplitVideoDurationPerClipHint = QLabel(self.tr('片段时长：'))
            self.durationSplitVideoDurationPerClipBox = QLineEdit()
            self.durationSplitVideoDurationPerClipBox.setAlignment(Qt.AlignCenter)

            self.durationSplitVideoCutHint = QCheckBox(self.tr('指定时间段'))
            self.durationSplitVideoInputSeekStartHint = QLabel(self.tr('起始时刻：'))
            self.durationSplitVideoInputSeekStartBox = QLineEdit()
            self.durationSplitVideoInputSeekStartBox.setAlignment(Qt.AlignCenter)
            self.durationSplitVideoEndTimeHint = QLabel(self.tr('截止时刻：'))
            self.durationSplitVideoEndTimeBox = QLineEdit()
            self.durationSplitVideoEndTimeBox.setAlignment(Qt.AlignCenter)
            self.durationSplitVideoCutHint.clicked.connect(self.onDurationSplitSwitchClicked)

            self.timeValidator = QRegExpValidator(self)
            self.timeValidator.setRegExp(QRegExp(r'[0-9]{0,2}:?[0-9]{0,2}:?[0-9]{0,2}\.?[0-9]{0,2}'))
            self.durationSplitVideoDurationPerClipBox.setValidator(self.timeValidator)
            self.durationSplitVideoInputSeekStartBox.setValidator(self.timeValidator)
            self.durationSplitVideoEndTimeBox.setValidator(self.timeValidator)

            self.durationSplitVideoRunButton = QPushButton(self.tr('运行'))
            self.durationSplitVideoRunButton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

            self.durationSplitVideoInputSeekStartHint.hide()
            self.durationSplitVideoInputSeekStartBox.hide()
            self.durationSplitVideoEndTimeHint.hide()
            self.durationSplitVideoEndTimeBox.hide()

            self.durationSplitVideoInputBox.textChanged.connect(self.setdurationSplitOutputFolder)
            self.durationSplitVideoInputButton.clicked.connect(self.durationSplitInputButtonClicked)
            self.durationSplitVideoRunButton.clicked.connect(self.onDurationSplitRunButtonClicked)


            self.durationSplitVideoInputWidgetLayout = QHBoxLayout()  # 输入文件
            self.durationSplitVideoInputWidgetLayout.addWidget(self.durationSplitVideoInputBox, 2)
            self.durationSplitVideoInputWidgetLayout.addWidget(self.durationSplitVideoInputButton, 1)
            self.durationSplitVideoInputWidgetLayout.setContentsMargins(0, 0, 0, 0)
            self.durationSplitVideoInputWidget = QWidget()
            self.durationSplitVideoInputWidget.setLayout(self.durationSplitVideoInputWidgetLayout)
            self.durationSplitVideoInputWidget.setContentsMargins(0, 0, 0, 0)

            self.durationSplitVideoStartEndTimeWidgetLayout = QHBoxLayout()  # 指定时间段
            self.durationSplitVideoStartEndTimeWidgetLayout.addWidget(self.durationSplitVideoInputSeekStartHint, 1)
            self.durationSplitVideoStartEndTimeWidgetLayout.addWidget(self.durationSplitVideoInputSeekStartBox, 1)
            self.durationSplitVideoStartEndTimeWidgetLayout.addSpacing(50)
            self.durationSplitVideoStartEndTimeWidgetLayout.addWidget(self.durationSplitVideoEndTimeHint, 1)
            self.durationSplitVideoStartEndTimeWidgetLayout.addWidget(self.durationSplitVideoEndTimeBox, 1)
            self.durationSplitVideoStartEndTimeWidgetLayout.setContentsMargins(0, 0, 0, 0)
            self.durationSplitVideoStartEndTimeWidget = QWidget()
            self.durationSplitVideoStartEndTimeWidget.setLayout(self.durationSplitVideoStartEndTimeWidgetLayout)
            self.durationSplitVideoStartEndTimeWidget.setContentsMargins(0, 0, 0, 0)

            self.durationSplitVdeoFormLayout = QFormLayout()
            self.durationSplitVdeoFormLayout.addRow(self.durationSplitVideoInputHint, self.durationSplitVideoInputWidget)
            self.durationSplitVdeoFormLayout.addRow(self.durationSplitVideoOutputHint, self.durationSplitVideoOutputBox)
            self.durationSplitVdeoFormLayout.addRow(self.durationSplitVideoDurationPerClipHint, self.durationSplitVideoDurationPerClipBox)
            self.durationSplitVdeoFormLayout.addRow(self.durationSplitVideoCutHint, self.durationSplitVideoStartEndTimeWidget)

            self.durationSplitVdeoHboxLayout = QHBoxLayout()
            self.durationSplitVdeoHboxLayout.setContentsMargins(0, 0, 0, 0)
            self.durationSplitVdeoHboxLayout.addLayout(self.durationSplitVdeoFormLayout, 3)
            self.durationSplitVdeoHboxLayout.addWidget(self.durationSplitVideoRunButton, 0)

            self.durationSplitVideoLayout.addLayout(self.durationSplitVdeoHboxLayout)  # 在主垂直布局添加选项的表单布局
            self.durationSplitVideoLayout.addStretch(1)

        self.masterLayout.addSpacing(5)

        # 根据大小分割片段
        if True:
            self.sizeSplitVideoGroup = QGroupBox(self.tr('根据指定大小分割片段'))
            self.sizeSplitVideoLayout = QVBoxLayout()
            self.sizeSplitVideoGroup.setLayout(self.sizeSplitVideoLayout)
            self.masterLayout.addWidget(self.sizeSplitVideoGroup)

            self.sizeSplitVideoInputHint = QLabel(self.tr('输入路径：'))
            self.sizeSplitVideoInputBox = MyQLine()
            self.sizeSplitVideoInputButton = QPushButton(self.tr('选择文件'))

            self.sizeSplitVideoOutputHint = QLabel(self.tr('输出文件夹：'))
            self.sizeSplitVideoOutputBox = MyQLine()
            self.sizeSplitVideoOutputBox.setReadOnly(True)

            self.sizeSplitVideoOutputSizeHint = QLabel(self.tr('片段大小(MB)：'))
            self.sizeSplitVideoOutputSizeBox = QLineEdit()
            self.sizeSplitVideoOutputSizeBox.setAlignment(Qt.AlignCenter)

            self.sizeValidator = QRegExpValidator(self)
            self.sizeValidator.setRegExp(QRegExp(r'\d+\.?\d*'))
            self.sizeSplitVideoOutputSizeBox.setValidator(self.sizeValidator)

            self.sizeSplitVideoCutHint = QCheckBox(self.tr('指定时间段'))
            self.sizeSplitVideoCutHint.clicked.connect(self.onSizeSplitSwitchClicked)
            self.sizeSplitVideoInputSeekStartHint = QLabel(self.tr('起始时刻：'))
            self.sizeSplitVideoInputSeekStartBox = QLineEdit()
            self.sizeSplitVideoInputSeekStartBox.setAlignment(Qt.AlignCenter)
            self.sizeSplitVideoEndTimeHint = QLabel(self.tr('截止时刻：'))
            self.sizeSplitVideoEndTimeBox = QLineEdit()
            self.sizeSplitVideoEndTimeBox.setAlignment(Qt.AlignCenter)

            self.timeValidator = QRegExpValidator(self)
            self.timeValidator.setRegExp(QRegExp(r'[0-9]{0,2}:?[0-9]{0,2}:?[0-9]{0,2}\.?[0-9]{0,2}'))
            self.sizeSplitVideoInputSeekStartBox.setValidator(self.timeValidator)
            self.sizeSplitVideoEndTimeBox.setValidator(self.timeValidator)

            self.sizeSplitVideoRunButton = QPushButton(self.tr('运行'))
            self.sizeSplitVideoRunButton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

            self.sizeSplitVideoInputSeekStartHint.hide()
            self.sizeSplitVideoInputSeekStartBox.hide()
            self.sizeSplitVideoEndTimeHint.hide()
            self.sizeSplitVideoEndTimeBox.hide()

            self.sizeSplitVideoInputBox.textChanged.connect(self.setSizeSplitOutputFolder)
            self.sizeSplitVideoInputButton.clicked.connect(self.sizeSplitInputButtonClicked)
            self.sizeSplitVideoRunButton.clicked.connect(self.onSizeSplitRunButtonClicked)


            self.sizeSplitVideoInputWidgetLayout = QHBoxLayout()  # 输入文件
            self.sizeSplitVideoInputWidgetLayout.addWidget(self.sizeSplitVideoInputBox, 2)
            self.sizeSplitVideoInputWidgetLayout.addWidget(self.sizeSplitVideoInputButton, 1)
            self.sizeSplitVideoInputWidgetLayout.setContentsMargins(0, 0, 0, 0)
            self.sizeSplitVideoInputWidget = QWidget()
            self.sizeSplitVideoInputWidget.setLayout(self.sizeSplitVideoInputWidgetLayout)
            self.sizeSplitVideoInputWidget.setContentsMargins(0, 0, 0, 0)

            self.sizeSplitVideoStartEndTimeWidgetLayout = QHBoxLayout()  # 指定时间段
            self.sizeSplitVideoStartEndTimeWidgetLayout.addWidget(self.sizeSplitVideoInputSeekStartHint, 1)
            self.sizeSplitVideoStartEndTimeWidgetLayout.addWidget(self.sizeSplitVideoInputSeekStartBox, 1)
            self.sizeSplitVideoStartEndTimeWidgetLayout.addSpacing(50)
            self.sizeSplitVideoStartEndTimeWidgetLayout.addWidget(self.sizeSplitVideoEndTimeHint, 1)
            self.sizeSplitVideoStartEndTimeWidgetLayout.addWidget(self.sizeSplitVideoEndTimeBox, 1)
            self.sizeSplitVideoStartEndTimeWidgetLayout.setContentsMargins(0, 0, 0, 0)
            self.sizeSplitVideoStartEndTimeWidget = QWidget()
            self.sizeSplitVideoStartEndTimeWidget.setLayout(self.sizeSplitVideoStartEndTimeWidgetLayout)
            self.sizeSplitVideoStartEndTimeWidget.setContentsMargins(0, 0, 0, 0)

            self.sizeSplitVdeoFormLayout = QFormLayout()
            self.sizeSplitVdeoFormLayout.addRow(self.sizeSplitVideoInputHint, self.sizeSplitVideoInputWidget)
            self.sizeSplitVdeoFormLayout.addRow(self.sizeSplitVideoOutputHint, self.sizeSplitVideoOutputBox)
            self.sizeSplitVdeoFormLayout.addRow(self.sizeSplitVideoOutputSizeHint, self.sizeSplitVideoOutputSizeBox)
            self.sizeSplitVdeoFormLayout.addRow(self.sizeSplitVideoCutHint, self.sizeSplitVideoStartEndTimeWidget)

            self.sizeSplitVdeoHboxLayout = QHBoxLayout()
            self.sizeSplitVdeoHboxLayout.setContentsMargins(0, 0, 0, 0)
            self.sizeSplitVdeoHboxLayout.addLayout(self.sizeSplitVdeoFormLayout, 3)
            self.sizeSplitVdeoHboxLayout.addWidget(self.sizeSplitVideoRunButton, 0)

            self.sizeSplitVideoLayout.addLayout(self.sizeSplitVdeoHboxLayout)  # 在主垂直布局添加选项的表单布局
            self.sizeSplitVideoLayout.addStretch(1)


    def onSubtitleSplitSwitchClicked(self):
        if self.subtitleSplitSwitch.isChecked():
            self.subtitleSplitStartTimeHint.show()
            self.subtitleSplitStartTimeBox.show()
            self.subtitleSplitEndTimeHint.show()
            self.subtitleSplitEndTimeBox.show()
        else:
            self.subtitleSplitStartTimeHint.hide()
            self.subtitleSplitStartTimeBox.hide()
            self.subtitleSplitEndTimeHint.hide()
            self.subtitleSplitEndTimeBox.hide()

    def onDurationSplitSwitchClicked(self):
        if self.durationSplitVideoCutHint.isChecked():
            self.durationSplitVideoInputSeekStartHint.show()
            self.durationSplitVideoInputSeekStartBox.show()
            self.durationSplitVideoEndTimeHint.show()
            self.durationSplitVideoEndTimeBox.show()
        else:
            self.durationSplitVideoInputSeekStartHint.hide()
            self.durationSplitVideoInputSeekStartBox.hide()
            self.durationSplitVideoEndTimeHint.hide()
            self.durationSplitVideoEndTimeBox.hide()

    def onSizeSplitSwitchClicked(self):
        if self.sizeSplitVideoCutHint.isChecked():
            self.sizeSplitVideoInputSeekStartHint.show()
            self.sizeSplitVideoInputSeekStartBox.show()
            self.sizeSplitVideoEndTimeHint.show()
            self.sizeSplitVideoEndTimeBox.show()
        else:
            self.sizeSplitVideoInputSeekStartHint.hide()
            self.sizeSplitVideoInputSeekStartBox.hide()
            self.sizeSplitVideoEndTimeHint.hide()
            self.sizeSplitVideoEndTimeBox.hide()

    def setSubtitleSplitOutputFolder(self):
        inputPath = self.subtitleSplitInputBox.text()
        if inputPath != '':
            outputFolder = os.path.splitext(inputPath)[0] + '/'
            self.subtitleSplitOutputBox.setText(outputFolder)
        else:
            self.subtitleSplitOutputBox.setText('')

    def setdurationSplitOutputFolder(self):
        inputPath = self.durationSplitVideoInputBox.text()
        if inputPath != '':
            outputFolder = os.path.splitext(inputPath)[0] + '/'
            self.durationSplitVideoOutputBox.setText(outputFolder)
        else:
            self.durationSplitVideoOutputBox.setText('')

    def setSizeSplitOutputFolder(self):
        inputPath = self.sizeSplitVideoInputBox.text()
        if inputPath != '':
            outputFolder = os.path.splitext(inputPath)[0] + '/'
            self.sizeSplitVideoOutputBox.setText(outputFolder)
        else:
            self.sizeSplitVideoOutputBox.setText('')

    def subtitleSplitInputButtonClicked(self):
        filename = QFileDialog().getOpenFileName(self, self.tr('打开文件'), None, self.tr('所有文件(*)'))
        if filename[0] != '':
            self.subtitleSplitInputBox.setText(filename[0])
        return True

    def subtitleSplitSubtitleFileInputButtonClicked(self):
        filename = QFileDialog().getOpenFileName(self, self.tr('打开文件'), None, self.tr('所有文件(*)'))
        if filename[0] != '':
            self.subtitleSplitSubtitleFileInputBox.setText(filename[0])
        return True

    def durationSplitInputButtonClicked(self):
        filename = QFileDialog().getOpenFileName(self, self.tr('打开文件'), None, self.tr('所有文件(*)'))
        if filename[0] != '':
            self.durationSplitVideoInputBox.setText(filename[0])
        return True

    def sizeSplitInputButtonClicked(self):
        filename = QFileDialog().getOpenFileName(self, self.tr('打开文件'), None, self.tr('所有文件(*)'))
        if filename[0] != '':
            self.sizeSplitVideoInputBox.setText(filename[0])
        return True

    def onSubtitleSplitRunButtonClicked(self):
        inputFile = self.subtitleSplitInputBox.text()
        subtitleFile = self.subtitleSplitSubtitleFileInputBox.text()
        outputFolder = self.subtitleSplitOutputBox.text()

        cutSwitchValue = self.subtitleSplitSwitch.isChecked()
        cutStartTime = self.subtitleSplitStartTimeBox.text()
        cutEndTime = self.subtitleSplitEndTimeBox.text()

        subtitleOffset = self.subtitleOffsetBox.value()

        if inputFile != '' and subtitleFile != '':
            window = Console(mainWindow)

            output = window.consoleBox
            outputForFFmpeg = window.consoleBoxForFFmpeg

            thread = SubtitleSplitVideoThread(mainWindow)

            thread.ffmpegOutputOption = self.ffmpegOutputOptionBox.currentText()

            thread.inputFile = inputFile
            thread.subtitleFile = subtitleFile
            thread.outputFolder = outputFolder

            thread.cutSwitchValue = cutSwitchValue
            thread.cutStartTime = cutStartTime
            thread.cutEndTime = cutEndTime
            thread.subtitleOffset = subtitleOffset

            thread.exportClipSubtitle = self.exportClipSubtitleSwitch.isChecked()
            thread.subtitleNumberPerClip = self.subtitleNumberPerClipBox.value()

            thread.output = output

            thread.signal.connect(output.print)
            thread.signalForFFmpeg.connect(outputForFFmpeg.print)

            window.thread = thread  # 把这里的剪辑子进程赋值给新窗口，这样新窗口就可以在关闭的时候也把进程退出

            thread.start()
            print(123)

    def onDurationSplitRunButtonClicked(self):
        inputFile = self.durationSplitVideoInputBox.text()
        outputFolder = self.durationSplitVideoOutputBox.text()

        durationPerClip = self.durationSplitVideoDurationPerClipBox.text()

        cutSwitchValue = self.durationSplitVideoCutHint.isChecked()
        cutStartTime = self.durationSplitVideoInputSeekStartBox.text()
        cutEndTime = self.durationSplitVideoEndTimeBox.text()

        if inputFile != '' and durationPerClip != '':
            window = Console(mainWindow)

            output = window.consoleBox
            outputForFFmpeg = window.consoleBoxForFFmpeg

            thread = DurationSplitVideoThread(mainWindow)

            thread.ffmpegOutputOption = self.ffmpegOutputOptionBox.currentText()


            thread.inputFile = inputFile
            thread.outputFolder = outputFolder

            thread.durationPerClip = durationPerClip

            thread.cutSwitchValue = cutSwitchValue
            thread.cutStartTime = cutStartTime
            thread.cutEndTime = cutEndTime

            thread.output = output
            thread.outputForFFmpeg = outputForFFmpeg

            thread.signal.connect(output.print)
            thread.signalForFFmpeg.connect(outputForFFmpeg.print)

            window.thread = thread  # 把这里的剪辑子进程赋值给新窗口，这样新窗口就可以在关闭的时候也把进程退出

            thread.start()

    def onSizeSplitRunButtonClicked(self):
        inputFile = self.sizeSplitVideoInputBox.text()
        outputFolder = self.sizeSplitVideoOutputBox.text()

        sizePerClip = self.sizeSplitVideoOutputSizeBox.text()

        cutSwitchValue = self.sizeSplitVideoCutHint.isChecked()
        cutStartTime = self.sizeSplitVideoInputSeekStartBox.text()
        cutEndTime = self.sizeSplitVideoEndTimeBox.text()

        if inputFile != '' and sizePerClip != '':
            window = Console(mainWindow)

            output = window.consoleBox
            outputForFFmpeg = window.consoleBoxForFFmpeg

            thread = SizeSplitVideoThread(mainWindow)

            thread.ffmpegOutputOption = self.ffmpegOutputOptionBox.currentText()


            thread.inputFile = inputFile
            thread.outputFolder = outputFolder

            thread.sizePerClip = sizePerClip

            thread.cutSwitchValue = cutSwitchValue
            thread.cutStartTime = cutStartTime
            thread.cutEndTime = cutEndTime

            thread.output = output

            thread.signal.connect(output.print)
            thread.signalForFFmpeg.connect(outputForFFmpeg.print)

            window.thread = thread  # 把这里的剪辑子进程赋值给新窗口，这样新窗口就可以在关闭的时候也把进程退出

            thread.start()

# 连接片段
class FFmpegConcatTab(QWidget):
    def __init__(self):
        super().__init__()
        self.fileList = []
        self.initUI()

    def drop(self):
        # print('12345')
        pass
    def initUI(self):
        self.inputHintLabel = QLabel(self.tr('点击列表右下边的加号添加要合并的视频片段：'))
        self.fileListWidget = FileListWidget(self)  # 文件表控件
        self.fileListWidget.setAcceptDrops(True)

        self.fileListWidget.doubleClicked.connect(self.fileListWidgetDoubleClicked)
        # self.fileListWidget.setLineWidth(1)

        self.masterVLayout = QVBoxLayout()
        self.masterVLayout.addWidget(self.inputHintLabel)
        self.masterVLayout.addWidget(self.fileListWidget)

        self.buttonHLayout = QHBoxLayout()
        self.upButton = QPushButton('↑')
        self.upButton.clicked.connect(self.upButtonClicked)
        self.downButton = QPushButton('↓')
        self.downButton.clicked.connect(self.downButtonClicked)
        self.reverseButton = QPushButton(self.tr('倒序'))
        self.reverseButton.clicked.connect(self.reverseButtonClicked)
        self.addButton = QPushButton('+')
        self.addButton.clicked.connect(self.addButtonClicked)
        self.fileListWidget.signal.connect(self.filesDrop)
        self.delButton = QPushButton('-')
        self.delButton.clicked.connect(self.delButtonClicked)
        self.buttonHLayout.addWidget(self.upButton)
        self.buttonHLayout.addWidget(self.downButton)
        self.buttonHLayout.addWidget(self.reverseButton)
        self.buttonHLayout.addWidget(self.addButton)
        self.buttonHLayout.addWidget(self.delButton)
        self.masterVLayout.addLayout(self.buttonHLayout)

        self.outputFileWidgetLayout = QHBoxLayout()
        self.outputHintLabel = QLabel(self.tr('输出：'))
        self.outputFileLineEdit = MyQLine()
        self.outputFileSelectButton = QPushButton(self.tr('选择保存位置'))
        self.outputFileSelectButton.clicked.connect(self.outputFileSelectButtonClicked)
        self.outputFileWidgetLayout.addWidget(self.outputHintLabel)
        self.outputFileWidgetLayout.addWidget(self.outputFileLineEdit)
        self.outputFileWidgetLayout.addWidget(self.outputFileSelectButton)
        self.masterVLayout.addLayout(self.outputFileWidgetLayout)

        self.methodVLayout = QVBoxLayout()

        self.concatRadioButton = QRadioButton(self.tr('concat格式衔接，不重新解码、编码（快、无损、要求格式一致）'))
        self.tsRadioButton = QRadioButton(self.tr('先转成 ts 格式，再衔接，要解码、编码（用于合并不同格式）'))
        self.concatFilterVStream0RadioButton = QRadioButton(self.tr('concat滤镜衔接（视频为Stream0），要解码、编码'))
        self.concatFilterAStream0RadioButton = QRadioButton(self.tr('concat滤镜衔接（音频为Stream0），要解码、编码'))
        self.methodVLayout.addWidget(self.concatRadioButton)
        self.methodVLayout.addWidget(self.tsRadioButton)
        self.methodVLayout.addWidget(self.concatFilterVStream0RadioButton)
        self.methodVLayout.addWidget(self.concatFilterAStream0RadioButton)

        self.finalCommandBoxLayout = QVBoxLayout()
        self.finalCommandEditBox = QPlainTextEdit()
        self.finalCommandEditBox.setPlaceholderText(self.tr('这里是自动生成的总命令'))
        self.runCommandButton = QPushButton(self.tr('运行'))
        self.runCommandButton.clicked.connect(self.runCommandButtonClicked)
        self.finalCommandBoxLayout.addWidget(self.finalCommandEditBox)
        self.finalCommandBoxLayout.addWidget(self.runCommandButton)

        self.bottomLayout = QHBoxLayout()
        self.bottomLayout.addLayout(self.methodVLayout)
        self.bottomLayout.addLayout(self.finalCommandBoxLayout)

        self.masterVLayout.addLayout(self.bottomLayout)
        self.setLayout(self.masterVLayout)

        self.refreshFileList()

        self.concatRadioButton.clicked.connect(lambda: self.concatMethodButtonClicked('concatFormat'))
        self.concatFilterVStream0RadioButton.clicked.connect(
            lambda: self.concatMethodButtonClicked('concatFilterVStreamFirst'))
        self.tsRadioButton.clicked.connect(lambda: self.concatMethodButtonClicked('tsConcat'))
        self.concatFilterAStream0RadioButton.clicked.connect(
            lambda: self.concatMethodButtonClicked('concatFilterAStreamFirst'))
        self.outputFileLineEdit.textChanged.connect(self.generateFinalCommand)
        self.concatRadioButton.setChecked(True)
        self.concatMethod = 'concatFormat'

    def filesDrop(self, list):
        self.fileList += list
        self.refreshFileList()

    def refreshFileList(self):
        self.fileListWidget.clear()
        self.fileListWidget.addItems(self.fileList)
        self.generateFinalCommand()

    def concatMethodButtonClicked(self, method):
        self.concatMethod = method
        self.generateFinalCommand()

    def fileListWidgetDoubleClicked(self):
        # print(True)
        result = QMessageBox.warning(self, self.tr('清空列表'), self.tr('是否确认清空列表？'), QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if result == QMessageBox.Yes:
            self.fileList.clear()
            self.refreshFileList()

    def upButtonClicked(self):
        itemCurrentPosition = self.fileListWidget.currentRow()
        if itemCurrentPosition > 0:
            temp = self.fileList[itemCurrentPosition]
            self.fileList.insert(itemCurrentPosition - 1, temp)
            self.fileList.pop(itemCurrentPosition + 1)
            self.refreshFileList()
            self.fileListWidget.setCurrentRow(itemCurrentPosition - 1)

    def downButtonClicked(self):
        itemCurrentPosition = self.fileListWidget.currentRow()
        if itemCurrentPosition > -1 and itemCurrentPosition < len(self.fileList) - 1:
            temp = self.fileList[itemCurrentPosition]
            self.fileList.insert(itemCurrentPosition + 2, temp)
            self.fileList.pop(itemCurrentPosition)
            self.refreshFileList()
            self.fileListWidget.setCurrentRow(itemCurrentPosition + 1)

    def reverseButtonClicked(self):
        self.fileList.reverse()
        self.refreshFileList()

    def addButtonClicked(self):
        fileNames, _ = QFileDialog().getOpenFileNames(self, self.tr('添加音视频文件'), None)
        if self.fileList == [] and fileNames != []:
            tempName = fileNames[0]
            tempNameParts = os.path.splitext(tempName)
            self.outputFileLineEdit.setText(tempNameParts[0] + 'out' + tempNameParts[1])
        self.fileList += fileNames
        self.refreshFileList()

    def delButtonClicked(self):
        currentPosition = self.fileListWidget.currentRow()
        if currentPosition > -1:
            self.fileList.pop(currentPosition)
            self.refreshFileList()
            if len(self.fileList) > 0:
                self.fileListWidget.setCurrentRow(currentPosition)

    def outputFileSelectButtonClicked(self):
        file, _ = QFileDialog.getSaveFileName(self, self.tr('选择保存位置'), 'out.mp4')
        if file != '':
            self.outputFileLineEdit.setText(file)

    def generateFinalCommand(self):
        if self.fileList != []:
            finalCommand = ''
            if self.concatMethod == 'concatFormat':
                finalCommand = '''ffmpeg -y -hide_banner -vsync 0 -safe 0 -f concat -i "fileList.txt" -c copy "%s"''' % self.outputFileLineEdit.text()
                f = open('fileList.txt', 'w', encoding='utf-8')
                with f:
                    for i in self.fileList:
                        f.write(r'''file '%s'
''' % i)
            elif self.concatMethod == 'tsConcat':
                inputTsFiles = ''
                for i in self.fileList:
                    tsOutPath = os.path.splitext(i)[0] + '.ts'
                    finalCommand = finalCommand + '''ffmpeg -y -hide_banner -i "%s" -c copy -bsf:v h264_mp4toannexb -f mpegts "%s" && ''' % (
                        i, tsOutPath)
                    inputTsFiles = inputTsFiles + tsOutPath + '|'
                if inputTsFiles[-1] == '|':
                    inputTsFiles = inputTsFiles[0:-1]
                # print(inputTsFiles)
                finalCommand += '''ffmpeg -hide_banner -y -i "concat:%s" -c copy -bsf:a aac_adtstoasc "%s"''' % (
                    inputTsFiles, self.outputFileLineEdit.text())
                pass
            elif self.concatMethod == 'concatFilterVStreamFirst':
                inputFiles = ''
                inputStreamIdentifiers = ''
                for i in range(len(self.fileList)):
                    inputFiles += '''-i "%s" ''' % self.fileList[i]
                    inputStreamIdentifiers += '''[%s:0][%s:1]''' % (i, i)
                finalCommand = '''ffmpeg -hide_banner -y %s -filter_complex "%sconcat=n=%s:v=1:a=1" "%s"''' % (
                    inputFiles, inputStreamIdentifiers, len(self.fileList), self.outputFileLineEdit.text())

            elif self.concatMethod == 'concatFilterAStreamFirst':
                inputFiles = ''
                inputStreamIdentifiers = ''
                for i in range(len(self.fileList)):
                    inputFiles += '''-i "%s" ''' % self.fileList[i]
                    inputStreamIdentifiers += '''[%s:1][%s:0]''' % (i, i)
                finalCommand = '''ffmpeg -hide_banner -y %s -filter_complex "%sconcat=n=%s:v=1:a=1" "%s"''' % (
                    inputFiles, inputStreamIdentifiers, len(self.fileList), self.outputFileLineEdit.text())
            self.finalCommandEditBox.setPlainText(finalCommand)
        else:
            self.finalCommandEditBox.clear()
            pass

    def runCommandButtonClicked(self):
        execute(self.finalCommandEditBox.toPlainText())


# 控制台输出
class ConsoleTab(QTableWidget):
    def __init__(self):
        super().__init__()
        self.initGui()

    def initGui(self):
        self.layout = QVBoxLayout()
        self.consoleEditBox = QTextEdit(self, readOnly=True)
        self.layout.addWidget(self.consoleEditBox)
        self.setLayout(self.layout)

# 帮助页面
class HelpTab(QWidget):
    def __init__(self):
        super().__init__()
        self.openHelpFileButton = QPushButton(self.tr('打开帮助文档'))
        self.ffmpegMannualNoteButton = QPushButton(self.tr('查看作者的 FFmpeg 笔记'))
        self.openVideoHelpButtone = QPushButton(self.tr('查看视频教程'))
        self.openGiteePage = QPushButton(self.tr('当前版本是 %s，到 Gitee 检查新版本') % version)
        self.openGithubPage = QPushButton(self.tr('当前版本是 %s，到 Github 检查新版本') % version)
        self.linkToDiscussPage = QPushButton(self.tr('加入 QQ 群'))
        self.tipButton = QPushButton(self.tr('打赏作者'))

        self.openHelpFileButton.setMaximumHeight(100)
        self.ffmpegMannualNoteButton.setMaximumHeight(100)
        self.openVideoHelpButtone.setMaximumHeight(100)
        self.openGiteePage.setMaximumHeight(100)
        self.openGithubPage.setMaximumHeight(100)
        self.linkToDiscussPage.setMaximumHeight(100)
        self.tipButton.setMaximumHeight(100)

        self.openHelpFileButton.clicked.connect(self.openHelpDocument)
        self.ffmpegMannualNoteButton.clicked.connect(lambda: webbrowser.open(self.tr(r'https://hacpai.com/article/1595480295489')))
        self.openVideoHelpButtone.clicked.connect(lambda: webbrowser.open(self.tr(r'https://www.bilibili.com/video/BV18T4y1E7FF/')))
        self.openGiteePage.clicked.connect(lambda: webbrowser.open(self.tr(r'https://gitee.com/haujet/QuickCut/releases')))
        self.openGithubPage.clicked.connect(lambda: webbrowser.open(self.tr(r'https://github.com/HaujetZhao/QuickCut/releases')))
        self.linkToDiscussPage.clicked.connect(lambda: webbrowser.open(
            self.tr(r'https://qm.qq.com/cgi-bin/qm/qr?k=DgiFh5cclAElnELH4mOxqWUBxReyEVpm&jump_from=webapi')))
        self.tipButton.clicked.connect(lambda: SponsorDialog())

        self.masterLayout = QVBoxLayout()
        self.setLayout(self.masterLayout)
        self.masterLayout.addWidget(self.openHelpFileButton)
        self.masterLayout.addWidget(self.ffmpegMannualNoteButton)
        self.masterLayout.addWidget(self.openVideoHelpButtone)
        self.masterLayout.addWidget(self.openGiteePage)
        self.masterLayout.addWidget(self.openGithubPage)
        self.masterLayout.addWidget(self.linkToDiscussPage)
        self.masterLayout.addWidget(self.tipButton)

    def openHelpDocument(self):
        try:
            if platfm == 'Darwin':
                import shlex
                os.system("open " + shlex.quote(self.tr("./README_zh.html")))
            elif platfm == 'Windows':
                os.startfile(os.path.realpath(self.tr('./README_zh.html')))
        except:
            pass




############# 自定义控件 ################

class FileListWidget(QListWidget):
    """这个列表控件可以拖入文件"""
    signal = pyqtSignal(list)

    def __init__(self, type, parent=None):
        super(FileListWidget, self).__init__(parent)
        self.setAcceptDrops(True)

    def enterEvent(self, a0: QEvent) -> None:
        mainWindow.status.showMessage(self.tr('双击列表项可以清空文件列表'))

    def leaveEvent(self, a0: QEvent) -> None:
        mainWindow.status.showMessage('')

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
            self.signal.emit(links)
        else:
            event.ignore()

# 打赏对话框
class SponsorDialog(QDialog):
    def __init__(self, parent=None):
        super(SponsorDialog, self).__init__(parent)
        self.resize(784, 890)
        if platfm == 'Darwin':
            self.setWindowIcon(QIcon('misc/icon.icns'))
        else:
            self.setWindowIcon(QIcon('misc/icon.ico'))
        self.setWindowTitle(self.tr('打赏作者'))
        self.exec()

    def paintEvent(self, event):
        painter = QPainter(self)
        pixmap = QPixmap('./sponsor.jpg')
        painter.drawPixmap(self.rect(), pixmap)

# 可拖入文件的单行编辑框
class MyQLine(QLineEdit):
    """实现文件拖放功能"""
    signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        # self.setAcceptDrops(True) # 设置接受拖放动作

    def dragEnterEvent(self, e):
        if True:
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):  # 放下文件后的动作
        if platfm == 'Windows':
            path = e.mimeData().text().replace('file:///', '')  # 删除多余开头
        else:
            path = e.mimeData().text().replace('file://', '')  # 对于 Unix 类系统只删掉两个 '/' 就行了
        self.setText(path)
        self.signal.emit(path)

# 命令输出窗口中的多行文本框
class OutputBox(QTextEdit):
    # 定义一个 QTextEdit 类，写入 print 方法。用于输出显示。
    def __init__(self, parent=None):
        super(OutputBox, self).__init__(parent)
        self.setReadOnly(True)

    def print(self, text):
        try:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertText(text)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
        except:
            pass
        pass

# 命令输出窗口中的多行文本框，此处用于接收语音识别识别出的文本
class OutputLineBox(QLineEdit):
    # 定义一个 QTextEdit 类，写入 print 方法。用于输出显示。
    def __init__(self, parent=None):
        super(OutputLineBox, self).__init__(parent)


# 可以状态栏提示的标签
class HintLabel(QLabel):

    hint = None

    def __init__(self, text):
        super().__init__()
        self.setText(text)
        # self.setAlignment(Qt.AlignCenter)

    def enterEvent(self, *args, **kwargs):
        if self.hint != None:
            try:
                mainWindow.status.showMessage(self.hint)
            except:
                pass

    def leaveEvent(self, *args, **kwargs):
        if self.hint != None:
            try:
                mainWindow.status.showMessage('')
            except:
                pass

# 可以状态栏提示的 ComboBox
class HintCombobox(QComboBox):

    hint = None

    def __init__(self):
        super().__init__()

    def enterEvent(self, *args, **kwargs):
        if self.hint != None:
            try:
                mainWindow.status.showMessage(self.hint)
            except:
                pass

    def leaveEvent(self, *args, **kwargs):
        if self.hint != None:
            try:
                mainWindow.status.showMessage('')
            except:
                pass





############# 自定义信号 ################

class ApiUpdated(QObject):
    signal = pyqtSignal(bool)

    def broadCastUpdates(self):
        self.signal.emit(True)


class Stream(QObject):
    # 用于将控制台的输出定向到一个槽
    newText = pyqtSignal(str)

    def write(self, text):
        self.newText.emit(str(text))
        QApplication.processEvents()




############# 子窗口 ################

class Console(QMainWindow):
    # 这个 console 是个子窗口，调用的时候要指定父窗口。例如：window = Console(mainWindow)
    # 里面包含一个 OutputBox, 可以将信号导到它的 print 方法。
    thread = None

    def __init__(self, parent=None):
        super(Console, self).__init__(parent)
        self.initGui()

    def initGui(self):
        self.setWindowTitle(self.tr('命令运行输出窗口'))
        self.resize(1300, 700)
        self.consoleBox = OutputBox() # 他就用于输出用户定义的打印信息
        self.consoleBoxForFFmpeg = OutputBox()  # 把ffmpeg的输出信息用它输出
        self.consoleBox.setParent(self)
        self.consoleBoxForFFmpeg.setParent(self)
        # self.masterLayout = QVBoxLayout()
        # self.masterLayout.addWidget(self.consoleBox)
        # self.masterLayout.addWidget(QPushButton())
        # self.setLayout(self.masterLayout)
        # self.masterWidget = QWidget()
        # self.masterWidget.setLayout(self.masterLayout)
        self.split = QSplitter(Qt.Vertical)
        self.split.addWidget(self.consoleBox)
        self.split.addWidget(self.consoleBoxForFFmpeg)
        self.setCentralWidget(self.split)
        self.show()

    def closeEvent(self, a0: QCloseEvent) -> None:
        try:
            try:
                if platfm == 'Windows':
                    # 这个方法可以杀死 subprocess 用了 shell=True 开启的子进程，新测好用！
                    # https://stackoverflow.com/questions/13243807/popen-waiting-for-child-process-even-when-the-immediate-child-has-terminated/13256908#13256908
                    subprocess.call("TASKKILL /F /PID {pid} /T".format(pid=self.thread.process.pid), startupinfo=subprocessStartUpInfo)
                else:
                    # 这个没新测，但是 Windows 用不了，只能用于 unix 类的系统
                    os.killpg(os.getpgid(self.thread.process.pid), signal.SIGTERM)
            except:
                pass
            try: # 用于自动剪辑线程，结束前清除其临时文件夹
                self.thread.removeTempFolder()
            except:
                pass

            try:
                self.thread.process.terminate()
            except:
                pass
            self.thread.exit()
            self.thread.setTerminationEnabled(True)
            self.thread.terminate()
        except:
            pass

class VoiceInputMethodTranscribeSubtitleWindow(QMainWindow):
    # 这是个子窗口，调用的时候要指定父窗口。例如：window = Console(mainWindow)
    # 里面包含一个 OutputBox, 可以将信号导到它的 print 方法。
    thread = None
    mode = 0  # 零代表半自动模式
    inputFiePath = None  # 输入路径
    timestampFile = None # 时间戳辅助文件
    outputFilePath = None  # 输出路径
    shortcutOfInputMethod = None  # 输入法的快捷键
    startTime = None  # 确定起始时间
    ffmpegWavGenThread = None
    continueToTrans = True # 默认在全自动模式下一句完成时继续下一轮
    transEngine = None

    def __init__(self, parent=None):
        super(VoiceInputMethodTranscribeSubtitleWindow, self).__init__(parent)
        self.ffmpegWavGenThread = FFmpegWavGenThread()
        self.initGui()

    def initGui(self):
        self.setWindowTitle(self.tr('语音输入法转写字幕工作窗口'))
        self.resize(1300, 700)
        self.hintConsoleBox = OutputBox() # 他就用于输出提示用户的信息
        self.finalResultBox = OutputBox()  # 输出总结果
        self.finalResultBox.setReadOnly(False)
        self.transInputBox = OutputLineBox()  # 临时听写框

        self.buttonLayout = QHBoxLayout()
        self.pauseButton = QPushButton(self.tr('暂停'))
        self.pauseButton.setEnabled(False)
        self.continueButton = QPushButton(self.tr('继续'))
        self.continueButton.setEnabled(False)
        self.pauseButton.clicked.connect(self.pauseThread)
        self.continueButton.clicked.connect(self.startThread)
        self.buttonLayout.addWidget(self.pauseButton)
        self.buttonLayout.addWidget(self.continueButton)



        # 设置父控件
        self.hintConsoleBox.setParent(self)
        self.finalResultBox.setParent(self)
        self.transInputBox.setParent(self)

        # 设置窗口布局
        self.masterWidget = QWidget()
        self.setCentralWidget(self.masterWidget)
        self.masterLayout = QVBoxLayout()
        self.masterLayout.setSpacing(30)
        self.masterWidget.setLayout(self.masterLayout)

        # 添加部件
        self.masterLayout.addWidget(self.hintConsoleBox, 2)
        self.masterLayout.addWidget(self.finalResultBox, 4)
        self.masterLayout.addWidget(self.transInputBox, 1)
        self.masterLayout.addLayout(self.buttonLayout, 1)

        self.show()

        self.hintConsoleBox.print(self.tr('正在生成 wav 文件\n'))

    def initParams(self):
        self.srtIndex = 0  # 初始化第一条字幕的序号
        if os.path.exists(self.outputFilePath):
            self.srtFile = open(os.path.splitext(self.outputFilePath)[0] + '.srt', 'r', encoding='utf-8')
            with self.srtFile:
                content = self.srtFile.read()
                if content != '':
                    self.finalResultBox.setText(content + '\n')  # 先读取已经存在的 srt
                    subtitleLists = list(srt.parse(content))  # 从已存在的文件中读取字幕
                    self.srtIndex += len(subtitleLists)  # 如果已经有，那就将字幕向前移
                    self.hintConsoleBox.print(self.tr('检测到已存在同名字幕文件，已有 %s 条字幕，将会自动载入到下面的编辑框\n') % self.srtIndex)
                    self.hintConsoleBox.print(self.tr('如果不希望接着已有内容做字幕，请手动删除已存在的字幕文件\n'))

            self.srtFile = open(os.path.splitext(self.outputFilePath)[0] + '.srt', 'w', encoding='utf-8')
        else:
            self.srtFile = open(os.path.splitext(self.outputFilePath)[0] + '.srt', 'w', encoding='utf-8')
        self.ffmpegWavGenThread.signal.connect(self.getFFmpegFinishSignal) #
        self.ffmpegWavGenThread.start()
        self.thread.offsetTime = self.startTime
        self.thread.srtIndex = self.srtIndex
        self.thread.resultTextBox = self.transInputBox  # 把语音识别结果的输入框给线程
        self.thread.shortcutKey = self.shortcutOfInputMethod  # 把快捷键
        self.thread.signal.connect(self.printSignalReceived)
        self.thread.signalOfSubtitle.connect(self.signalOfSubtitleReceived)

    def startThread(self):
        self.continueToTrans = True
        if self.mode == 1:
            self.pauseButton.setEnabled(True)
        self.thread.start()
        self.finalResultBox.setReadOnly(True)
        self.continueButton.setEnabled(False)

    def pauseThread(self):
        self.continueToTrans = False
        self.pauseButton.setEnabled(False)
        self.transInputBox.setFocus()

    def printSignalReceived(self, text):
        print(text)

    def signalOfSubtitleReceived(self, srtObject):
        self.finalResultBox.setReadOnly(False)
        subtitle = srt.compose([srtObject], start_index=srtObject.index + 1)
        self.finalResultBox.print(subtitle)
        self.hintConsoleBox.print(self.tr('第 %s 句识别完毕！\n') % self.thread.srtIndex)
        if srtObject.content == '':
            self.hintConsoleBox.print(self.tr('片段识别结果是空白，有可能音频设置有误，请查看视频教程：https://www.bilibili.com/video/BV1wT4y177kD/\n'))
        if self.mode == 0:  # 只有在半自动模式，才在收到结果时恢复继续按键
            self.continueButton.setEnabled(True)
        else:
            if self.continueToTrans == False: # 当在全自动模式，暂停后，收到了结果，让继续键变可用
                self.continueButton.setEnabled(True)
            if self.continueToTrans == True:
                self.startThread()

    def getFFmpegFinishSignal(self, wavFile): # 得到 wav 文件，
        self.regionsList = self.transEngine.getRegions(wavFile) # 得到片段
        if self.regionsList == False:
            self.hintConsoleBox.print('无法从输入文件转出 wav 文件，请先用”pip show auditok“检查下 auditok 的版本，如果低于 0.2，请使用 ”pip install git+https://gitee.com/haujet/auditok“ 或 ”pip install git+https://github.com/amsehili/auditok“ 安装最新版本的 auditok，如果 auditok 版本没有问题，那就可能是输入文件不是标准音视频文件。 ')
            return
        self.wavFile = wavFile
        self.regionsListLength = len(self.regionsList)
        self.thread.transEngine = self.transEngine
        self.thread.regionsList = self.regionsList
        self.thread.regionsListLength = self.regionsListLength
        print(self.regionsListLength)
        self.hintConsoleBox.print(self.tr('已得到 wav 文件，并分段，共有 %s 段\n') % self.regionsListLength)
        self.hintConsoleBox.print(self.tr('该功能需要设置电脑一番，所以请确保已看过视频教程：\n'))
        self.hintConsoleBox.print(self.tr('关闭本页面后，下方输入框的内容会自动保存到 %s 中\n') % self.outputFilePath)
        if self.mode == 0: #只有在半自动模式，才在收到结果时恢复继续按键
            self.hintConsoleBox.print(self.tr('现在按下 继续 键开始听写音频\n'))
            self.continueButton.setEnabled(True)
        if self.mode == 1: # 如果是自动模式，那就即刻发车！
            time.sleep(1)
            self.startThread()


    def closeEvent(self, a0: QCloseEvent) -> None:
        try: # 尝试将字幕格式化后写入输出文件。
            originalSubtitle = self.finalResultBox.toPlainText()
            processedSubtitle = srt.compose(list(srt.parse(originalSubtitle)), reindex=True, start_index=1, strict=True)
            with self.srtFile:
                self.srtFile.write(processedSubtitle)
        except:
            pass
        try:
            os.remove(self.wavFile)
        except:
            pass
        try:
            keyboard.release(self.shortcutOfInputMethod) # 这里是防止在关闭页面时，语音输入快捷键还按着
        except:
            pass
        try:
            self.thread.exit()
        except:
            pass
        try:
            self.thread.setTerminationEnabled(True)
            self.thread.terminate()
        except:
            pass


class _UpdateDialogUI:
    def setup_ui(self, UpdateDialog):
        UpdateDialog.setObjectName('UpdateDialog')
        UpdateDialog.resize(350, 500)
        UpdateDialog.setWindowFlags(
            Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.Dialog)
        if platfm == 'Darwin':
            UpdateDialog.setWindowIcon(QIcon('misc/icon.icns'))
        else:
            UpdateDialog.setWindowIcon(QIcon('misc/icon.ico'))
        size_policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(UpdateDialog.sizePolicy()
                                      .hasHeightForWidth())
        UpdateDialog.setSizePolicy(size_policy)
        UpdateDialog.setAutoFillBackground(False)
        UpdateDialog.setSizeGripEnabled(False)
        self.horizontal_layout = QHBoxLayout(UpdateDialog)
        self.horizontal_layout.setContentsMargins(10, 10, 10, 10)
        self.horizontal_layout.setObjectName('horizontal_layout')
        self.grid_layout = QGridLayout()
        self.grid_layout.setObjectName('grid_layout')
        self.gitee_button = QPushButton(UpdateDialog)
        self.gitee_button.setEnabled(False)
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(self.gitee_button.sizePolicy()
                                      .hasHeightForWidth())
        self.gitee_button.setSizePolicy(size_policy)
        self.gitee_button.setMaximumSize(QSize(16777215, 30))
        self.gitee_button.setAutoDefault(False)
        self.gitee_button.setObjectName('gitee_button')
        self.grid_layout.addWidget(self.gitee_button, 1, 1, 1, 1)
        self.close_button = QPushButton(UpdateDialog)
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(self.close_button.sizePolicy()
                                      .hasHeightForWidth())
        self.close_button.setSizePolicy(size_policy)
        self.close_button.setMaximumSize(QSize(16777215, 30))
        self.close_button.setAutoDefault(False)
        self.close_button.setDefault(False)
        self.close_button.setObjectName('close_button')
        self.grid_layout.addWidget(self.close_button, 1, 2, 1, 1)
        self.github_button = QPushButton(UpdateDialog)
        self.github_button.setEnabled(False)
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(self.github_button.sizePolicy()
                                      .hasHeightForWidth())
        self.github_button.setSizePolicy(size_policy)
        self.github_button.setMaximumSize(QSize(16777215, 30))
        self.github_button.setAutoDefault(False)
        self.github_button.setObjectName('github_button')
        self.grid_layout.addWidget(self.github_button, 1, 0, 1, 1)
        self.update_info_text = QTextEdit(UpdateDialog)
        self.update_info_text.setEnabled(True)
        self.update_info_text.setDocumentTitle('')
        self.update_info_text.setUndoRedoEnabled(False)
        self.update_info_text.setReadOnly(True)
        self.update_info_text.setObjectName('update_info_text')
        self.grid_layout.addWidget(self.update_info_text, 0, 0, 1, 3)
        self.horizontal_layout.addLayout(self.grid_layout)

        self.retranslate_ui(UpdateDialog)
        QMetaObject.connectSlotsByName(UpdateDialog)

    def retranslate_ui(self, UpdateDialog):
        _translate = QCoreApplication.translate
        UpdateDialog.setWindowTitle(_translate('UpdateDialog', '发现更新'))
        self.gitee_button.setText(_translate('UpdateDialog', '前往Gitee下载'))
        self.close_button.setText(_translate('UpdateDialog', '关闭'))
        self.github_button.setText(
            _translate('UpdateDialog', '前往Github下载'))
        self.update_info_text.setPlaceholderText(
            _translate('UpdateDialog', '获取更新信息失败'))


class UpdateDialog(QDialog, _UpdateDialogUI):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui(self)
        self.close_button.clicked.connect(self.close)
        self.github_set = False
        self.gitee_set = False
        self.update_avail = False

    @pyqtSlot(tuple)
    def set_result(self, result):
        site, avail, info, url = result
        assert site in ('github', 'gitee')

        # Prepare buttons
        if site == 'github':
            if url is not None:
                self.github_button.clicked.connect(
                    lambda: webbrowser.open(url))
            self.github_button.setEnabled(avail)
            self.github_set = True
        else:
            if url is not None:
                self.gitee_button.clicked.connect(
                    lambda: webbrowser.open(url))
            self.gitee_button.setEnabled(avail)
            self.gitee_set = True
        # Prepare release info
        if avail:
            self.update_avail = True
        if self.update_info_text.toMarkdown() == '' and info is not None:
            self.update_info_text.setMarkdown(info)

        # Show dialog when it has both results of Github and Gitee, and
        # update is available
        if self.github_set and self.gitee_set and self.update_avail:
            self.show()


############# 子进程################
class _BufferedReaderForFFmpeg(io.BufferedReader):
    """Method `newline` overriden to *also* treat `\\r` as a line break."""
    def readline(self, size=-1):
        if hasattr(self, "peek"):
            def nreadahead():
                readahead = self.peek(1)
                if not readahead:
                    return 1
                n = (readahead.find(b'\r') + 1) \
                    or (readahead.find(b'\n') + 1) or len(readahead)
                if size >= 0:
                    n = min(n, size)
                return n
        else:
            def nreadahead():
                return 1
        if size is None:
            size = -1
        else:
            try:
                size_index = size.__index__
            except AttributeError:
                raise TypeError(f"{size!r} is not an integer")
            else:
                size = size_index()
        res = bytearray()
        while size < 0 or len(res) < size:
            b = self.read(nreadahead())
            if not b:
                break
            res += b
            if os.linesep == '\r\n':
                # Windows
                if res.endswith(b'\r'):
                    if self.peek(1).startswith(b'\n'):
                        # \r\n encountered
                        res += self.read(1)
                    break
            else:
                # Unix
                if res.endswith(b'\r') or res.endswith(b'\n'):
                    break
        return bytes(res)


class CommandThread(QThread):
    signal = pyqtSignal(str)
    signalForFFmpeg = pyqtSignal(str)

    output = None  # 用于显示输出的控件，如一个 QEditBox，它需要有自定义的 print 方法。

    outputTwo = None

    command = None

    def __init__(self, parent=None):
        super(CommandThread, self).__init__(parent)

    def print(self, text):
        self.signal.emit(text)
    def printForFFmpeg(self, text):
        self.signalForFFmpeg.emit(text)

    def run(self):
        self.print(self.tr('开始执行命令\n'))
        try:
            if platfm == 'Windows':
                # command = self.command.encode('gbk').decode('gbk')
                self.process = subprocess.Popen(self.command, shell=True, stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT, startupinfo=subprocessStartUpInfo)
            else:
                self.process = subprocess.Popen(self.command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                start_new_session=True)
        except:
            self.print(self.tr('出错了，本次运行的命令是：\n\n%s\n\n你可以将上面这行命令复制到 cmd 窗口运行下，看看报什么错，如果自己解决不了，把那个报错信息发给开发者。如果是 you-get 和 youtube-dl 的问题，请查看视频教程：https://www.bilibili.com/video/BV18T4y1E7FF?p=5\n\n') % self.command)
        try:
            stdout = _BufferedReaderForFFmpeg(self.process.stdout.raw)
            while True:
                line = stdout.readline()
                if not line:
                    break
                try:
                    self.printForFFmpeg(line.decode('utf-8'))
                except UnicodeDecodeError:
                    self.printForFFmpeg(line.decode('gbk'))
        except:
            self.print(
                self.tr('''出错了，本次运行的命令是：\n\n%s\n\n你可以将上面这行命令复制到 cmd 窗口运行下，看看报什么错，如果自己解决不了，把那个报错信息发给开发者\n''') % self.command)
        self.print(self.tr('\n命令执行完毕\n'))


# 根据字幕分割视频
class SubtitleSplitVideoThread(QThread):
    signal = pyqtSignal(str)
    signalForFFmpeg = pyqtSignal(str)

    ffmpegOutputOption = ''

    inputFile = None
    subtitleFile = None
    outputFolder = None

    cutSwitchValue = None
    cutStartTime = None
    cutEndTime = None

    subtitleOffset = None

    exportClipSubtitle = None

    clipOutputOption = ''
    subtitleNumberPerClip = 1
    # clipOutputOption = '-c copy'

    output = None  # 用于显示输出的控件，如一个 QEditBox，它需要有自定义的 print 方法。

    inputFile = None

    def __init__(self, parent=None):
        super(SubtitleSplitVideoThread, self).__init__(parent)

    def print(self, text):
        self.signal.emit(text)

    def printForFFmpeg(self, text):
        self.signalForFFmpeg.emit(text)

    def run(self):
        # try:
        subtitleSplit = os.path.splitext(self.subtitleFile)
        subtitleName = subtitleSplit[0]
        subtitleExt = subtitleSplit[1]
        inputFileExt = os.path.splitext(self.inputFile)[1]
        # clipOutputOption = ''

        if self.cutSwitchValue != 0:
            if self.cutStartTime != '':  # 如果开始时间不为空，转换为秒数
                self.cutStartTime = strTimeToSecondsTime(self.cutStartTime)
                print(self.cutStartTime)
            if self.cutEndTime != '':  # 如果结束时间不为空，转换为秒数
                self.cutEndTime = strTimeToSecondsTime(self.cutEndTime)
                print(self.cutEndTime)

        if re.match('\.ass', subtitleExt, re.IGNORECASE):
            self.print(self.tr('字幕是ass格式，先转换成srt格式\n'))
            command = '''ffmpeg -y -hide_banner -i "%s" "%s" ''' % (self.subtitleFile, subtitleName + '.srt')
            self.process = subprocess.call(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           universal_newlines=True)
            # for line in self.process.stdout:
            #     self.print(line)
            self.print(self.tr('格式转换完成\n'))
            self.subtitleFile = subtitleName + '.srt'
            try:
                f = open(self.subtitleFile, 'r')
                with f:
                    subtitleContent = f.read()
                try:
                    os.remove(self.subtitleFile)
                except:
                    self.print(self.tr('删除生成的srt字幕失败'))
            except:
                f = open(self.subtitleFile, 'r', encoding='utf-8')
                with f:
                    subtitleContent = f.read()
                try:
                    os.remove(self.subtitleFile)
                except:
                    self.print(self.tr('删除生成的srt字幕失败'))
        elif re.match('\.mkv', subtitleExt, re.IGNORECASE):
            self.print(self.tr('字幕是 mkv 格式，先转换成srt格式\n'))
            command = '''ffmpeg -y -hide_banner -i "%s" -an -vn "%s" ''' % (self.subtitleFile, subtitleName + '.srt')
            self.process = subprocess.call(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           universal_newlines=True)
            # for line in self.process.stdout:
            #     self.print(line)
            self.print(self.tr('格式转换完成\n'))
            self.subtitleFile = subtitleName + '.srt'
            try:
                f = open(self.subtitleFile, 'r')
                with f:
                    subtitleContent = f.read()
                try:
                    os.remove(self.subtitleFile)
                except:
                    self.print(self.tr('删除生成的srt字幕失败'))
            except:
                f = open(self.subtitleFile, 'r', encoding='utf-8')
                with f:
                    subtitleContent = f.read()
                try:
                    os.remove(self.subtitleFile)
                except:
                    self.print(self.tr('删除生成的srt字幕失败'))
        elif re.match('\.vtt', subtitleExt, re.IGNORECASE):
            self.print(self.tr('字幕是 vtt 格式，先转换成srt格式\n'))
            command = '''ffmpeg -y -hide_banner -i "%s" -an -vn "%s" ''' % (self.subtitleFile, subtitleName + '.srt')
            self.process = subprocess.call(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           universal_newlines=True)
            # for line in self.process.stdout:
            #     self.print(line)
            self.print(self.tr('格式转换完成\n'))
            self.subtitleFile = subtitleName + '.srt'
            try:
                f = open(self.subtitleFile, 'r')
                with f:
                    subtitleContent = f.read()
                try:
                    os.remove(self.subtitleFile)
                except:
                    self.print(self.tr('删除生成的srt字幕失败'))
            except:
                f = open(self.subtitleFile, 'r', encoding='utf-8')
                with f:
                    subtitleContent = f.read()
                try:
                    os.remove(self.subtitleFile)
                except:
                    self.print(self.tr('删除生成的srt字幕失败'))
        elif re.match('\.srt', subtitleExt, re.IGNORECASE):
            try:
                with open(self.subtitleFile, 'r', encoding='utf-8') as f:
                    subtitleContent = f.read()
            except:
                with open(self.subtitleFile, 'r', encoding='gbk') as f:
                    subtitleContent = f.read()
        else:
            self.print(
                self.tr('字幕格式只支持 srt、ass 和 vtt，以及带内置字幕的 mkv 文件，暂不支持您所选的字幕。\n\n如果您的字幕输入是 mkv 而失败了，则有可能您的 mkv 视频没有字幕流，画面中的字幕是烧到画面中的。'))
            return False
        # srt.parse
        srtObject = srt.parse(subtitleContent)
        srtList = list(srtObject)
        totalNumber = len(srtList)
        try:
            os.mkdir(self.outputFolder)
        except:
            self.print(self.tr('创建输出文件夹失败，可能是已经创建上了\n'))
        for i in range(0, totalNumber, self.subtitleNumberPerClip):
            # Subtitle(index=2, start=datetime.timedelta(seconds=11, microseconds=800000), end=datetime.timedelta(seconds=13, microseconds=160000), content='该喝水了', proprietary='')
            self.print(self.tr('总共有 %s 段要处理，现在开始导出第 %s 段……\n') % (int(totalNumber / self.subtitleNumberPerClip), int(
                (i + self.subtitleNumberPerClip) / self.subtitleNumberPerClip)))
            start = srtList[i].start.seconds + (srtList[i].start.microseconds / 1000000) + self.subtitleOffset
            end = srtList[i + self.subtitleNumberPerClip - 1].end.seconds + (
                        srtList[i].end.microseconds / 1000000) + self.subtitleOffset
            duration = end - start
            if start < 0:
                start = 0
            if end < 0:
                end = 0
            if self.cutSwitchValue != 0:  # 如果确定要剪切一个区间
                print
                if self.cutStartTime != '':  # 如果起始时间不为空
                    if end < self.cutStartTime:
                        continue
                if self.cutEndTime != '':
                    if start > self.cutEndTime:
                        continue
            index = format(srtList[i].index, '0>6d')
            command = 'ffmpeg -y -ss %s -to %s -i "%s" %s "%s"' % (
            start, end, self.inputFile, self.ffmpegOutputOption, self.outputFolder + index + '.' + inputFileExt)
            if platfm == 'Windows':
                self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                universal_newlines=True, encoding='utf-8',
                                                startupinfo=subprocessStartUpInfo)
            else:
                self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                universal_newlines=True, encoding='utf-8')
            for line in self.process.stdout:
                self.printForFFmpeg(line)
                pass
            if self.exportClipSubtitle != 0:
                subtitles = []
                for j in range(0, self.subtitleNumberPerClip, 1):
                    startTime = (srtList[i + j].start.seconds + srtList[i + j].start.microseconds / 1000000) - (
                                srtList[i].start.seconds + srtList[i].start.microseconds / 1000000)
                    startSeconds = int(startTime)
                    startMicroseconds = startTime * 1000 % 1000 * 1000
                    duration = (srtList[i + j].end.seconds + srtList[i + j].end.microseconds / 1000000) - (
                                srtList[i + j].start.seconds + srtList[i + j].start.microseconds / 1000000)
                    endTime = startTime + duration
                    endSeconds = int(endTime)
                    endMicroseconds = endTime * 1000 % 1000 * 1000
                    startTime = datetime.timedelta(seconds=startSeconds, microseconds=startMicroseconds)
                    endTime = datetime.timedelta(seconds=endSeconds, microseconds=endMicroseconds)
                    subContent = srtList[i + j].content

                    subtitle = srt.Subtitle(index=j + 1, start=startTime, end=endTime, content=subContent)
                    subtitles.append(subtitle)
                srtSub = srt.compose(subtitles, reindex=True, start_index=1, strict=True)
                srtPath = self.outputFolder + index + '.srt'
                with open(srtPath, 'w+') as srtFile:
                    srtFile.write(srtSub)
                pass

        self.print(self.tr('导出完成\n'))

        # self.print(os.path.splitext(self.subtitleFile)[1])
        # except:
        #     self.print('分割过程出错了')

# 根据时长分割视频
class DurationSplitVideoThread(QThread):
    signal = pyqtSignal(str)
    signalForFFmpeg = pyqtSignal(str)

    ffmpegOutputOption = ''

    inputFile = None
    outputFolder = None

    durationPerClip = None

    cutSwitchValue = None
    cutStartTime = 1
    cutEndTime = None

    clipOutputOption = ''
    # clipOutputOption = '-c copy'

    output = None  # 用于显示输出的控件，如一个 QEditBox，它需要有自定义的 print 方法。

    def __init__(self, parent=None):
        super(DurationSplitVideoThread, self).__init__(parent)

    def print(self, text):
        self.signal.emit(text)

    def printForFFmpeg(self, text):
        self.signalForFFmpeg.emit(text)

    def run(self):
        视频的起点时刻 = 0
        视频文件的总时长 = getMediaTimeLength(self.inputFile)  # 得到视频的整个时长

        视频处理的起点时刻 = 视频的起点时刻
        视频处理的总时长 = 视频文件的总时长

        self.ext = os.path.splitext(self.inputFile)[1]  # 得到输出后缀
        每段输出视频的时长 = float(strTimeToSecondsTime(self.durationPerClip))  # 将片段时长从字符串变为浮点数

        # 如果设置了从中间一段进行分段，那么就重新设置一下起始时间和总共时长
        if self.cutSwitchValue == True:
            视频处理的起点时刻 = strTimeToSecondsTime(self.cutStartTime)
            if 视频处理的起点时刻 >= 视频文件的总时长:
                视频处理的起点时刻 = 0
            用户输入的截止时刻 = strTimeToSecondsTime(self.cutEndTime)
            if 用户输入的截止时刻 > 0:
                if 用户输入的截止时刻 > 视频文件的总时长:
                    视频处理的总时长 = 视频文件的总时长 - 视频处理的起点时刻
                else:
                    视频处理的总时长 = 用户输入的截止时刻 - 视频处理的起点时刻
            else:
                视频处理的总时长 = 视频文件的总时长 - 视频处理的起点时刻

        try:
            os.mkdir(self.outputFolder)
        except:
            self.print(self.tr('创建输出文件夹失败，可能是已经创建上了\n'))
        continueToCut = True
        i = 1
        totalClipNumber = math.ceil(视频处理的总时长 / 每段输出视频的时长)
        ffmpegOutputOption = []
        self.print(self.tr('总共要处理的时长：%s 秒      导出的每个片段时长：%s 秒 \n') % (视频处理的总时长, 每段输出视频的时长))
        while continueToCut:
            if 视频处理的总时长 <= 每段输出视频的时长:
                每段输出视频的时长 = 视频处理的总时长  # 当剩余时间的长度已经小于需要的片段时,就将最后这段时间长度设为剩余时间
                continueToCut = False  # 并且将循环判断依据设为否  也就是剪完下面这一段之后，就不要再继续循环了
            self.print(self.tr('总共有 %s 个片段要导出，现在导出第 %s 个……\n') % (totalClipNumber, i))
            # command = ['ffmpeg', 'ss', self.cutStartTime, 't', 每段输出视频的时长, 'i', self.inputFile] + ffmpegOutputOption + [ self.outputFolder + '.' + self.ext]
            command = '''ffmpeg -y -ss %s -t %s -i "%s" %s "%s"''' % (
            视频处理的起点时刻, 每段输出视频的时长, self.inputFile, self.ffmpegOutputOption, self.outputFolder + format(i, '0>6d') + self.ext)
            # self.print(command)
            if platfm == 'Windows':
                self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                universal_newlines=True, encoding='utf-8',
                                                startupinfo=subprocessStartUpInfo)
            else:
                self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                universal_newlines=True, encoding='utf-8')
            for line in self.process.stdout:
                self.printForFFmpeg(line)
                pass
            视频处理的起点时刻 += 每段输出视频的时长
            视频处理的总时长 -= 每段输出视频的时长
            i += 1
        self.print(self.tr('导出完成\n'))

# 根据大小分割视频
class SizeSplitVideoThread(QThread):
    signal = pyqtSignal(str)
    signalForFFmpeg = pyqtSignal(str)

    ffmpegOutputOption = ''

    inputFile = None
    outputFolder = None

    sizePerClip = None

    cutSwitchValue = None
    cutStartTime = 1
    cutEndTime = None

    clipOutputOption = ''
    # clipOutputOption = '-c copy'

    output = None  # 用于显示输出的控件，如一个 QEditBox，它需要有自定义的 print 方法。

    def __init__(self, parent=None):
        super(SizeSplitVideoThread, self).__init__(parent)

    def print(self, text):
        self.signal.emit(text)

    def printForFFmpeg(self, text):
        self.signalForFFmpeg.emit(text)

    def run(self):
        视频的起点时刻 = 0
        视频文件的总时长 = getMediaTimeLength(self.inputFile)  # 得到视频的整个时长

        视频处理的起点时刻 = 视频的起点时刻
        视频处理的总时长 = 视频文件的总时长

        self.ext = os.path.splitext(self.inputFile)[1]  # 得到输出后缀
        每段输出视频的大小 = int(float(self.sizePerClip) * 1024 * 1024)

        # 如果设置了从中间一段进行分段，那么就重新设置一下起始时间和总共时长
        if self.cutSwitchValue == True:
            视频处理的起点时刻 = strTimeToSecondsTime(self.cutStartTime)
            if 视频处理的起点时刻 >= 视频文件的总时长:
                视频处理的起点时刻 = 0
            用户输入的截止时刻 = strTimeToSecondsTime(self.cutEndTime)
            if 用户输入的截止时刻 > 0:
                if 用户输入的截止时刻 > 视频文件的总时长:
                    视频处理的总时长 = 视频文件的总时长 - 视频处理的起点时刻
                else:
                    视频处理的总时长 = 用户输入的截止时刻 - 视频处理的起点时刻
            else:
                视频处理的总时长 = 视频文件的总时长 - 视频处理的起点时刻

        总共应导出的时长 = 视频处理的总时长
        try:
            os.mkdir(self.outputFolder)
        except:
            self.print(self.tr('创建输出文件夹失败，可能是已经创建上了\n'))
        continueToCut = True
        i = 1
        ffmpegOutputOption = []
        self.print(self.tr('总共要处理的时长：%s 秒      导出的每个片段大小：%sMB \n') % (视频处理的总时长, self.sizePerClip))
        self.print(self.tr('需要知晓的是：最后导出的视频体积一般会略微超过您预设的大小，比如你设置每个片段为 20MB，实际导出的片段可能会达到 21MB 左右。\n'))
        # 视频处理的总时长
        已导出的总时长 = 0
        while continueToCut:

            # command = ['ffmpeg', 'ss', self.cutStartTime, 't', 每段输出视频的时长, 'i', self.inputFile] + ffmpegOutputOption + [ self.outputFolder + '.' + self.ext]
            command = '''ffmpeg -y -ss %s -t %s -i "%s" -fs %s %s "%s"''' % (
                视频处理的起点时刻, 视频处理的总时长, self.inputFile, 每段输出视频的大小, self.ffmpegOutputOption, self.outputFolder + format(i, '0>6d') + self.ext)
            # self.print(command)
            if platfm == 'Windows':
                self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                universal_newlines=True, encoding='utf-8',
                                                startupinfo=subprocessStartUpInfo)
            else:
                self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                universal_newlines=True, encoding='utf-8')
            self.print(self.tr('\n\n\n\n\n\n\n还有 %s 秒时长的片段要导出，总共已经导出 %s 秒的视频，目前正在导出的是第 %s 个片段……\n') % (format(视频处理的总时长, '.1f'), format(已导出的总时长, '.1f'), i))
            for line in self.process.stdout:
                self.printForFFmpeg(line)
                pass
            新输出的视频的长度 = getMediaTimeLength(self.outputFolder + format(i, '0>6d') + self.ext)
            视频处理的起点时刻 += 新输出的视频的长度
            已导出的总时长 += 新输出的视频的长度
            视频处理的总时长 -= 新输出的视频的长度
            i += 1
            if 总共应导出的时长 - 已导出的总时长 < 1:
                continueToCut = False  # 并且将循环判断依据设为否  也就是剪完下面这一段之后，就不要再继续循环了
        self.print(self.tr('导出完成。\n'))
        self.print(self.tr('应导出 %s 秒，实际导出 %s 秒。\n') % (format(总共应导出的时长, '.1f'), format(已导出的总时长, '.1f')))




# FFmpeg 得到 wav 文件
class FFmpegWavGenThread(QThread):
    signal = pyqtSignal(str)
    mediaFile = None
    startTime = None
    endTime = None


    def __init__(self, parent=None):
        super(FFmpegWavGenThread, self).__init__(parent)


    def run(self):
        # 得到输入文件除了除了扩展名外的名字
        pathPrefix = os.path.splitext(self.mediaFile)[0]
        # ffmpeg 命令
        command = 'ffmpeg -hide_banner -y -ss %s -to %s -i "%s" -ac 1 -ar 16000 "%s.wav"' % (
            self.startTime, self.endTime, self.mediaFile, pathPrefix)
        if platfm == 'Windows':
            self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            universal_newlines=True, encoding='utf-8',
                                            startupinfo=subprocessStartUpInfo)
        else:
            self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            universal_newlines=True, encoding='utf-8')
        for line in self.process.stdout:
            pass
        self.signal.emit('%s.wav' % (pathPrefix))


def _request_retry(*, times=5):
    def decorator(wrapped):
        @wraps(wrapped)
        def wrapper(*args, **kwargs):
            counter = 1
            while counter <= times:
                try:
                    return wrapped(*args, **kwargs)
                except requests.RequestException as e:
                    if counter < times:
                        print(f'{wrapped} failed {counter} time(s): {e}. '
                              f'Retrying')
                    else:
                        print(f'{wrapped} failed {counter} time(s): {e}.')
                        raise
                    counter += 1
        return wrapper
    return decorator


class UpdateChecker:
    def __init__(self):
        self._github_thread, self._gitee_thread = QThread(), QThread()
        self._github_worker = _UpdateCheckerWorker('github')
        self._github_worker.moveToThread(self._github_thread)
        self._github_thread.started.connect(self._github_worker.run)
        self._gitee_worker = _UpdateCheckerWorker('gitee')
        self._gitee_worker.moveToThread(self._gitee_thread)
        self._gitee_thread.started.connect(self._gitee_worker.run)

        self._update_dialog = UpdateDialog()
        self._github_worker.signal.connect(self._update_dialog.set_result)
        self._gitee_worker.signal.connect(self._update_dialog.set_result)

    def check_for_update(self):
        self._github_thread.start()
        self._gitee_thread.start()

    @property
    def update_dialog(self):
        return self._update_dialog


class _UpdateCheckerWorker(QObject):
    _github_api = \
        'https://api.github.com/repos/HaujetZhao/QuickCut/releases/latest'
    _gitee_api = \
        'https://gitee.com/api/v5/repos/haujet/QuickCut/releases/latest'
    _gitee_release = 'https://gitee.com/haujet/QuickCut/releases'
    signal = pyqtSignal(tuple)

    def __init__(self, site, parent=None):
        super().__init__(parent)
        assert site in ('github', 'gitee')
        self._site = site

    @pyqtSlot()
    def run(self):
        try:
            result = self._make_request()
        except requests.RequestException:
            result = (self._site, False, None, None)
        self.signal.emit(result)

    @_request_retry()
    def _make_request(self):
        if self._site == 'github':
            api_url = self._github_api
        else:
            api_url = self._gitee_api
        r = requests.get(api_url, timeout=5)
        if r.status_code != 200:
            raise requests.HTTPError('status code is not 200')
        r_json = r.json()

        latest_version = r_json['tag_name']
        if latest_version.casefold() != version.casefold():
            update_avail = True
        else:
            update_avail = False

        if update_avail:
            update_info = r_json['body']
            if self._site == 'github':
                release_url = r_json['html_url']
            else:
                release_url = f'{self._gitee_release}/{latest_version}'
        else:
            update_info = None
            release_url = None
        return self._site, update_avail, update_info, release_url



############# 自定义方法 ################

def strTimeToSecondsTime(inputTime):
    if re.match(r'.+\.\d+', inputTime):
        pass
    else:  # 如果没有小数点，就加上小数点
        inputTime = inputTime + '.0'

    if re.match(r'\d+:\d+:\d+\.\d+', inputTime):
        temp = re.findall('\d+', inputTime)
        return float(temp[0]) * 3600 + float(temp[1]) * 60 + float(temp[2]) + float('0.' + temp[3])
    elif re.match(r'\d+:\d+\.\d+', inputTime):
        temp = re.findall('\d+', inputTime)
        return float(temp[0]) * 60 + float(temp[1]) + float('0.' + temp[2])
    elif re.match(r'\d+\.\d+', inputTime):
        temp = re.findall('\d+', inputTime)
        return float(temp[0]) + float('0.' + temp[1])
    elif re.match(r'\d+', inputTime):
        temp = re.findall('\d+', inputTime)
        return float(temp[0])
    else:
        return float(0)

# 得到视频长度
def getMediaTimeLength(inputFile):
    # 用于获取一个视频或者音频文件的长度
    # try:
    print('start getting info')
    info = pymediainfo.MediaInfo.parse(inputFile)
    print('info' + str(info))
    duration = 0
    print('info.tracks' + str(info.tracks))
    for track in info.tracks:
        print('track.duration' + str(track.duration))
        if float(track.duration) > duration:
            duration = track.duration
    return float(duration / 1000)
    # except:
        # return float(0)

    # 下面这是 ffprobe 的方法，暂时先不用了。
    # result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
    #                          "format=duration", "-of",
    #                          "default=noprint_wrappers=1:nokey=1", inputFile], shell=True,
    #                         stdout=subprocess.PIPE,
    #                         stderr=subprocess.STDOUT)
    # return float(result.stdout)

# 执行命令
def execute(command):
    # 判断一下系统，如果是windows系统，就直接将命令在命令行窗口中运行，避免在程序中运行时候的卡顿。
    # 主要是因为手上没有图形化的linux系统和mac os系统，不知道怎么打开他们的终端执行某个个命令，所以就将命令在程序中运行，输出到一个新窗口的文本编辑框。
    # system = platform.system()
    # if system == 'Windows':
    #     os.system('start cmd /k ' + command)
    # else:
    #     console = Console(mainWindow)
    #     console.runCommand(command)

    # 新方法，执行子进程，在新窗口输出
    thread = CommandThread()  # 新建一个子进程
    thread.command = command  # 将要执行的命令赋予子进程
    window = Console(mainWindow)  # 显示一个新窗口，用于显示子进程的输出
    output = window.consoleBox  # 获得新窗口中的输出控件
    outputForFFmpeg = window.consoleBoxForFFmpeg
    thread.signal.connect(output.print)  # 将 子进程中的输出信号 连接到 新窗口输出控件的输出槽
    thread.signalForFFmpeg.connect(outputForFFmpeg.print)  # 将 子进程中的输出信号 连接到 新窗口输出控件的输出槽
    window.thread = thread  # 把这里的剪辑子进程赋值给新窗口，这样新窗口就可以在关闭的时候也把进程退出
    thread.start()

# 检查环境变量中是否有程序，返回可执行程序，这个方法先不用，但是他有用，所以先存着
def getProgram(program):
    """
    Return the path for a given executable.
    """
    def is_exe(file_path):
        """
        Checks whether a file is executable.
        """
        return os.path.isfile(file_path) and os.access(file_path, os.X_OK)

    fpath, _ = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

def createDB():
    ########改用主数据库
    cursor = conn.cursor()
    result = cursor.execute('select * from sqlite_master where name = "%s";' % (ossTableName))
    # 将oss初始预设写入数据库
    if result.fetchone() == None:
        cursor.execute('''create table %s (
                                    id integer primary key autoincrement,
                                    provider text, 
                                    endPoint text, 
                                    bucketName text, 
                                    bucketDomain text,
                                    accessKeyId text, 
                                    accessKeySecret text)''' % ossTableName)
    else:
        print('oss 表单已存在')
    result = cursor.execute('select * from sqlite_master where name = "%s";' % (apiTableName))
    # 将api初始预设写入数据库
    if result.fetchone() == None:
        cursor.execute('''create table %s (
                                    id integer primary key autoincrement,
                                    name text, 
                                    provider text, 
                                    appKey text, 
                                    language text, 
                                    accessKeyId text, 
                                    accessKeySecret text
                                    )''' % apiTableName)
    else:
        print('api 表单已存在')
    result = cursor.execute('select * from sqlite_master where name = "%s";' % (preferenceTableName))
    # 将初始偏好设置写入数据库
    if result.fetchone() == None:
        cursor.execute('''create table %s (
                                            id integer primary key autoincrement,
                                            item text,
                                            value text
                                            )''' % preferenceTableName)

        cursor.execute('''insert into %s (item, value) values ('%s', '%s');''' % (
        preferenceTableName, 'hideToTrayWhenHitCloseButton', 'False'))
    else:
        print('偏好设置表单已存在')
    conn.commit()

def checkDBLanguage():
    result = conn.cursor().execute('select value from %s where item = "language";' % (preferenceTableName))
    if result.fetchone() == None:
        conn.cursor().execute('''insert into %s (item, value) values ('%s', '%s');''' % (preferenceTableName, 'language', '中文'))
    else:
        print('oss 表单已存在')
    result = conn.cursor().execute('select value from %s where item = "language";' % (preferenceTableName))
    return result.fetchone()[0]


def excepthook(exec_type, exec_val, exec_tb):
    with open('traceback.log', 'w') as f:
        formatted_tb = format_exception(exec_type, exec_val, exec_tb)
        print(*formatted_tb,
              '\n请将以上信息发给1292756898@qq.com，或提交到'
              'https://github.com/HaujetZhao/QuickCut/issues', file=f)
    msg = ('程序发生致命错误，即将退出。\n'
           '请查看同目录下的traceback.log获取详细错误信息。')
    """try:
        QMessageBox.critical(main, mainWindow.tr('致命错误'), mainWindow.tr(msg))
    except NameError:
        print('没有发现主窗口')
    sys.exit(1)"""


############# 程序入口 ################

def main():
    global app, conn, language, translator, apiUpdateBroadCaster, platfm, subprocessStartUpInfo, mainWindow, tray
    sys.excepthook = excepthook
    os.environ['PATH'] += os.pathsep + os.getcwd()
    app = QApplication(sys.argv)
    conn = sqlite3.connect(dbname)
    createDB()
    language = checkDBLanguage()  # 得到已设置的语言
    if language != '中文':
        print('language changed')
        translator = QTranslator()
        translator.load('./languages/%s.qm' % language)
        app.installTranslator(translator)
    apiUpdateBroadCaster = ApiUpdated()
    platfm = platform.system()
    if platfm == 'Windows':
        global subprocessStartUpInfo
        subprocessStartUpInfo = subprocess.STARTUPINFO()
        subprocessStartUpInfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
        subprocessStartUpInfo.wShowWindow = subprocess.SW_HIDE
    else:
        pass
    mainWindow = MainWindow()
    mainWindow.capsWriterTab.initCapsWriterStatus()  # 只有在 mainWindow 初始化完成后，才能启动 capsWriter
    if platfm == 'Darwin':
        tray = SystemTray(QIcon('misc/icon.icns'), mainWindow)
    else:
        tray = SystemTray(QIcon('misc/icon.ico'), mainWindow)
    sys.exit(app.exec_())
    conn.close()

if __name__ == '__main__':
    main()