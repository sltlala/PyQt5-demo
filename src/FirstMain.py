# GUIdemo.py
# Demo of GUI by PyQt5
# Copyright 2023 sltlala, CUG
# Crated：2023-06-06

from PyQt5.QtWidgets import QApplication, QMainWindow
import sys
import UI_py.Home

if __name__ == '__main__':
    app = QApplication(sys.argv)  # 创建应用程序对象
    MainWindow = QMainWindow()  # 创建主窗口
    ui = UI_py.Home.Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()  # 显示主窗口
    sys.exit(app.exec_())  # 在主线程中退出
