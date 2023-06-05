import sys
from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("登录")
        self.username_label = QLabel("用户名:")
        self.password_label = QLabel("密码:")
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.login_button = QPushButton("登录")
        self.register_button = QPushButton("注册")

        layout = QVBoxLayout()
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)
        layout.addWidget(self.register_button)

        self.setLayout(layout)

        self.login_button.clicked.connect(self.login)
        self.register_button.clicked.connect(self.register)

    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        # 在这里编写登录逻辑
        # 比较用户名和密码是否正确
        # 如果正确，显示登录成功的提示
        # 如果错误，显示登录失败的提示

        # 示例逻辑
        if username == "admin" and password == "admin":
            print("登录成功")
        else:
            print("登录失败")

    def register(self):
        username = self.username_input.text()
        password = self.password_input.text()

        # 在这里编写注册逻辑
        # 将用户名和密码保存到数据库或文件中

        # 示例逻辑
        print("注册成功")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = LoginDialog()
    dialog.show()
    sys.exit(app.exec_())
