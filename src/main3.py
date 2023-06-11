import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import UI_py.Home

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._update_checker = None
        self.initGui()

    def initGui(self):
        # 定义中心控件为多 tab 页面
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # 定义多个不同功能的 tab
        self.HomeTab = UI_py.Home.Home()  # 主要功能的 tab

        # 将不同功能的 tab 添加到主 tabWidget
        self.tabs.addTab(self.HomeTab, self.tr('Home'))
        self.setWindowTitle('Dss')
        # self.setWindowFlag(Qt.WindowStaysOnTopHint) # 始终在前台
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)  # 创建应用程序对象
    # MainWindow = QMainWindow()  # 创建主窗口
    ui = MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()  # 显示主窗口
    sys.exit(app.exec_())  # 在主线程中退出
