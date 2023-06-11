import sys

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtGui, QtWidgets

import Tab_UI.tab1
import UI_py.New_Build
dbname = './database.db'  # 存储预设的数据库名字
presetTableName = 'commandPreset'  # 存储预设的表单名字
preferenceTableName = 'preference'
styleFile = './style.css'  # 样式表的路径
finalCommand = ''
version = 'V1.0'

class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self._update_checker = None
		self.initGui()
		self.status = self.statusBar()

	def initGui(self):
		# 定义中心控件为多 tab 页面
		self.tabs = QTabWidget()
		self.setCentralWidget(self.tabs)

		# 定义多个不同功能的 tab
		self.HomeTab = HomeTab()
		self.ProductTrackTab = ProductTrackTab()
		self.PlatformSelectionTab = PlatformSelectionTab()
		self.KOL_InitialSelectionTab = KOL_InitialSelectionTab()
		self.KOL_CompareTab = KOL_CompareTab()
		self.KOL_ForecastTab = KOL_ForecastTab()
		self.FinalProposalTab = FinalProposalTab()

		# 将不同功能的 tab 添加到主 tabWidget
		self.tabs.addTab(self.HomeTab, self.tr('主页'))
		self.tabs.addTab(self.ProductTrackTab, self.tr('产品赛道'))
		self.tabs.addTab(self.PlatformSelectionTab, self.tr('平台选择'))
		self.tabs.addTab(self.KOL_InitialSelectionTab, self.tr('KOL初筛'))
		self.tabs.addTab(self.KOL_CompareTab, self.tr('KOL选择'))
		self.tabs.addTab(self.KOL_ForecastTab, self.tr('发展预测'))
		self.tabs.addTab(self.FinalProposalTab, self.tr('最终推荐方案'))

		self.adjustSize()
		self.show()

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
		if MainWindow.ConfigTab.hideToSystemTraySwitch.isChecked():
			event.ignore()
			self.hide()
		else:
			sys.stdout = sys.__stdout__
			super().closeEvent(event)


############# 不同功能的 Tab ################

class HomeTab(QWidget):
	def __init__(self):
		super().__init__()
		self.initGui()

	def initGui(self):
		Tab = QtWidgets.QWidget()
		ui = Tab_UI.tab1.Tab1()
		ui.setupUi(Tab)


class ProductTrackTab(QWidget):
	def __init__(self):
		super().__init__()
		self.initGui()

	def initGui(self):
		self.tab = QtWidgets.QWidget()

class PlatformSelectionTab(QWidget):
	def __init__(self):
		super().__init__()
		self.initGui()

	def initGui(self):
		self.tab = QtWidgets.QWidget()

class KOL_InitialSelectionTab(QWidget):
	def __init__(self):
		super().__init__()
		self.initGui()

	def initGui(self):
		self.tab = QtWidgets.QWidget()

class KOL_CompareTab(QWidget):
	def __init__(self):
		super().__init__()
		self.initGui()

	def initGui(self):
		self.tab = QtWidgets.QWidget()

class KOL_ForecastTab(QWidget):
	def __init__(self):
		super().__init__()
		self.initGui()

	def initGui(self):
		self.tab = QtWidgets.QWidget()

class FinalProposalTab(QWidget):
	def __init__(self):
		super().__init__()
		self.initGui()

	def initGui(self):
		self.tab = QtWidgets.QWidget()


def main():
	app = QApplication(sys.argv)
	mainWindow = MainWindow()
	mainWindow.show()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()