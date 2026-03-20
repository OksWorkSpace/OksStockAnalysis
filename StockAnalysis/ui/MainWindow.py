# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MainWindow.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QGroupBox, QHBoxLayout,
    QHeaderView, QLineEdit, QMainWindow, QMenuBar,
    QPushButton, QSizePolicy, QSpacerItem, QStatusBar,
    QTableView, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(648, 582)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBox_3 = QGroupBox(self.centralwidget)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.horizontalLayout = QHBoxLayout(self.groupBox_3)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.edit_data_folder = QLineEdit(self.groupBox_3)
        self.edit_data_folder.setObjectName(u"edit_data_folder")
        self.edit_data_folder.setReadOnly(True)

        self.horizontalLayout.addWidget(self.edit_data_folder)

        self.btn_data_folder = QPushButton(self.groupBox_3)
        self.btn_data_folder.setObjectName(u"btn_data_folder")

        self.horizontalLayout.addWidget(self.btn_data_folder)

        self.btn_krx_load = QPushButton(self.groupBox_3)
        self.btn_krx_load.setObjectName(u"btn_krx_load")

        self.horizontalLayout.addWidget(self.btn_krx_load)


        self.verticalLayout.addWidget(self.groupBox_3)

        self.groupBox_stock_day = QGroupBox(self.centralwidget)
        self.groupBox_stock_day.setObjectName(u"groupBox_stock_day")
        self.verticalLayout_2 = QVBoxLayout(self.groupBox_stock_day)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.chk_kospi = QCheckBox(self.groupBox_stock_day)
        self.chk_kospi.setObjectName(u"chk_kospi")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.chk_kospi.sizePolicy().hasHeightForWidth())
        self.chk_kospi.setSizePolicy(sizePolicy)
        self.chk_kospi.setMinimumSize(QSize(0, 0))

        self.horizontalLayout_2.addWidget(self.chk_kospi)

        self.chk_kosdaqg = QCheckBox(self.groupBox_stock_day)
        self.chk_kosdaqg.setObjectName(u"chk_kosdaqg")
        sizePolicy.setHeightForWidth(self.chk_kosdaqg.sizePolicy().hasHeightForWidth())
        self.chk_kosdaqg.setSizePolicy(sizePolicy)
        self.chk_kosdaqg.setMinimumSize(QSize(0, 0))

        self.horizontalLayout_2.addWidget(self.chk_kosdaqg)

        self.chk_kosdaq = QCheckBox(self.groupBox_stock_day)
        self.chk_kosdaq.setObjectName(u"chk_kosdaq")
        sizePolicy.setHeightForWidth(self.chk_kosdaq.sizePolicy().hasHeightForWidth())
        self.chk_kosdaq.setSizePolicy(sizePolicy)
        self.chk_kosdaq.setMinimumSize(QSize(0, 0))

        self.horizontalLayout_2.addWidget(self.chk_kosdaq)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.btn_run_model = QPushButton(self.groupBox_stock_day)
        self.btn_run_model.setObjectName(u"btn_run_model")
        sizePolicy.setHeightForWidth(self.btn_run_model.sizePolicy().hasHeightForWidth())
        self.btn_run_model.setSizePolicy(sizePolicy)

        self.horizontalLayout_2.addWidget(self.btn_run_model)


        self.verticalLayout_2.addLayout(self.horizontalLayout_2)

        self.tableView_stock = QTableView(self.groupBox_stock_day)
        self.tableView_stock.setObjectName(u"tableView_stock")

        self.verticalLayout_2.addWidget(self.tableView_stock)


        self.verticalLayout.addWidget(self.groupBox_stock_day)

        self.verticalLayout.setStretch(1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 648, 22))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("MainWindow", u"\ub370\uc774\ud130 \ud3f4\ub354", None))
        self.btn_data_folder.setText(QCoreApplication.translate("MainWindow", u"\ud3f4\ub354\uc120\ud0dd", None))
        self.btn_krx_load.setText(QCoreApplication.translate("MainWindow", u"\ubd88\ub7ec\uc624\uae30", None))
        self.groupBox_stock_day.setTitle(QCoreApplication.translate("MainWindow", u"\uc8fc\uc2dd \ud604\ud669", None))
        self.chk_kospi.setText(QCoreApplication.translate("MainWindow", u"KOSPI", None))
        self.chk_kosdaqg.setText(QCoreApplication.translate("MainWindow", u"KOSDAQ GLOBAL", None))
        self.chk_kosdaq.setText(QCoreApplication.translate("MainWindow", u"KOSDAQ", None))
        self.btn_run_model.setText(QCoreApplication.translate("MainWindow", u"\uc885\uac00\uc608\uce21", None))
    # retranslateUi

