from PyQt5.QtWidgets import *
from Login_module.login import Ui_LoginUi  # 导入login文件
from Login_module.Con_MySQL import *  # 导入数据库文件
from Login_module.call_regist import MainRegistWindow  # 导入注册文件
import sys
import configparser

global UserName
UserP = {}  # 定义一个存储密码账号的元组


class MainLoginWindow(QWidget, Ui_LoginUi):
	def __init__(self, parent=None):
		super(MainLoginWindow, self).__init__(parent)
		self.re = MainRegistWindow()  # 这边一定要加self
		self.setupUi(self)
		self.initUi()

	def initUi(self):
		self.IsRememberUser()
		self.UserName.setFocus()
		self.UserName.setPlaceholderText("请输入账号")
		self.PassWord.setPlaceholderText("请输入密码")
		self.PassWord.setEchoMode(QLineEdit.Password)  # 密码隐藏

		self.RegistButton.clicked.connect(self.regist_button)  # 跳转到注册页面
		self.re.SuccessReg.connect(self.Success_Regist)  # 注册或者取消跳转回来
		self.LoginButton.clicked.connect(self.login_button)  # 登录
		self.LogoutButton.clicked.connect(self.logout_button)  # 退出

	"""设置记住密码"""

	def IsRememberUser(self):
		config = configparser.ConfigParser()
		file = config.read('user.ini')  # 读取密码账户的配置文件
		config_dict = config.defaults()  # 返回包含实例范围默认值的字典
		self.account = config_dict['user_name']  # 获取账号信息
		self.UserName.setText(self.account)  # 写入账号上面
		if config_dict['remember'] == 'True':
			self.passwd = config_dict['password']
			self.PassWord.setText(self.passwd)
			self.RememberUser.setChecked(True)
		else:
			self.RememberUser.setChecked(False)

	"""设置配置文件格式"""

	def config_ini(self):
		self.account = self.UserName.text()
		self.passwd = self.PassWord.text()
		config = configparser.ConfigParser()
		if self.RememberUser.isChecked():
			config["DEFAULT"] = {
				"user_name": self.account,
				"password": self.passwd,
				"remember": self.RememberUser.isChecked()
			}
		else:
			config["DEFAULT"] = {
				"user_name": self.account,
				"password": "",
				"remember": self.RememberUser.isChecked()
			}
		with open('user.ini', 'w') as configfile:
			config.write((configfile))
		print(self.account, self.passwd)

	# 注册
	def regist_button(self):
		# 载入数据库
		# self.sql = Oper_Mysql()
		# self.sql.ZSGC_Mysql()
		self.re.show()
		w.close()

	# 登录
	def login_button(self):
		self.sql = Oper_Mysql()
		if QSqlDatabase.contains("qt_sql_default_connection"):
			db = QSqlDatabase.database("qt_sql_default_connection")
		else:
			db = QSqlDatabase.addDatabase("QMYSQL")
		Login_User = self.UserName.text()
		Login_Passwd = self.PassWord.text()
		# print(type(Login_User))
		# print(type(Login_Passwd))

		if Login_User == 0 or Login_Passwd.strip() == '':
			QMessageBox.information(self, "error", "输入错误")
		else:
			self.config_ini()  # 加载用户密码配置文件
			query = QSqlQuery()
			query.exec_("select *from Management")
			while query.next():
				UserID = str(query.value("M_UserID"))
				UserPasswd = query.value("M_PassWord")
				UserP[UserID] = UserPasswd
			length = len(UserP)
			for key in UserP:
				length = length - 1
				if key == Login_User and UserP[Login_User] == Login_Passwd:  # 密码和账号都对的情况下
					mess = QMessageBox()
					mess.setWindowTitle("Success")
					mess.setText("登录成功")
					mess.setStandardButtons(QMessageBox.Ok)
					mess.button(QMessageBox.Ok).animateClick(1000)  # 弹框定时关闭
					mess.exec_()
					print("登录成功")
					"""跳转到主界面"""
					self.MainWin.show()
					w.close()
					return True
				elif key != Login_User and length == 0:
					QMessageBox.information(self, "waining", "账号不存在", QMessageBox.Ok)
					return False
				elif key == Login_User and UserP[Login_User] != Login_Passwd:
					QMessageBox.information(self, "error!", "密码输入错误", QMessageBox.Ok)
					return False

	# 退出
	def logout_button(self):
		# 警告对话框
		messageBox = QMessageBox(QMessageBox.Warning, "警告", "是否退出系统！")
		Qyes = messageBox.addButton(self.tr("确认"), QMessageBox.YesRole)
		Qno = messageBox.addButton(self.tr("取消"), QMessageBox.NoRole)
		messageBox.setDefaultButton(Qno)  # 默认焦点
		messageBox.exec_()  # 保持
		if messageBox.clickedButton() == Qyes:
			w.close()
		else:
			return

	# 成功注册
	def Success_Regist(self):
		w.show()
		self.re.close()


if __name__ == "__main__":
	app = QApplication(sys.argv)
	w = MainLoginWindow()
	w.show()
	sys.exit(app.exec())

