# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ChartWidget.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGraphicsView, QGridLayout,
    QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QSpacerItem, QTextBrowser, QVBoxLayout, QWidget)

class Ui_ChartWidget(object):
    def setupUi(self, ChartWidget):
        if not ChartWidget.objectName():
            ChartWidget.setObjectName(u"ChartWidget")
        ChartWidget.resize(1031, 459)
        self.horizontalLayout = QHBoxLayout(ChartWidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.btn_search_news = QPushButton(ChartWidget)
        self.btn_search_news.setObjectName(u"btn_search_news")

        self.verticalLayout.addWidget(self.btn_search_news)

        self.textBrowser = QTextBrowser(ChartWidget)
        self.textBrowser.setObjectName(u"textBrowser")

        self.verticalLayout.addWidget(self.textBrowser)


        self.horizontalLayout.addLayout(self.verticalLayout)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_3 = QLabel(ChartWidget)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout_2.addWidget(self.label_3, 0, 0, 1, 1)

        self.check_candle = QCheckBox(ChartWidget)
        self.check_candle.setObjectName(u"check_candle")

        self.gridLayout_2.addWidget(self.check_candle, 0, 1, 1, 2)

        self.check_heikin = QCheckBox(ChartWidget)
        self.check_heikin.setObjectName(u"check_heikin")

        self.gridLayout_2.addWidget(self.check_heikin, 0, 3, 1, 2)

        self.label = QLabel(ChartWidget)
        self.label.setObjectName(u"label")

        self.gridLayout_2.addWidget(self.label, 1, 0, 1, 1)

        self.check_sma5 = QCheckBox(ChartWidget)
        self.check_sma5.setObjectName(u"check_sma5")
        self.check_sma5.setMinimumSize(QSize(0, 0))

        self.gridLayout_2.addWidget(self.check_sma5, 1, 1, 1, 1)

        self.check_sma10 = QCheckBox(ChartWidget)
        self.check_sma10.setObjectName(u"check_sma10")

        self.gridLayout_2.addWidget(self.check_sma10, 1, 2, 1, 1)

        self.check_sma20 = QCheckBox(ChartWidget)
        self.check_sma20.setObjectName(u"check_sma20")

        self.gridLayout_2.addWidget(self.check_sma20, 1, 3, 1, 1)

        self.check_sma60 = QCheckBox(ChartWidget)
        self.check_sma60.setObjectName(u"check_sma60")

        self.gridLayout_2.addWidget(self.check_sma60, 1, 4, 1, 1)

        self.check_sma200 = QCheckBox(ChartWidget)
        self.check_sma200.setObjectName(u"check_sma200")

        self.gridLayout_2.addWidget(self.check_sma200, 1, 5, 1, 1)

        self.label_2 = QLabel(ChartWidget)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout_2.addWidget(self.label_2, 2, 0, 1, 1)

        self.check_bb10 = QCheckBox(ChartWidget)
        self.check_bb10.setObjectName(u"check_bb10")

        self.gridLayout_2.addWidget(self.check_bb10, 2, 1, 1, 1)

        self.check_bb20 = QCheckBox(ChartWidget)
        self.check_bb20.setObjectName(u"check_bb20")

        self.gridLayout_2.addWidget(self.check_bb20, 2, 2, 1, 1)

        self.check_bb30 = QCheckBox(ChartWidget)
        self.check_bb30.setObjectName(u"check_bb30")

        self.gridLayout_2.addWidget(self.check_bb30, 2, 3, 1, 1)


        self.horizontalLayout_2.addLayout(self.gridLayout_2)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)


        self.verticalLayout_3.addLayout(self.horizontalLayout_2)

        self.graphicsView = QGraphicsView(ChartWidget)
        self.graphicsView.setObjectName(u"graphicsView")

        self.verticalLayout_3.addWidget(self.graphicsView)


        self.horizontalLayout.addLayout(self.verticalLayout_3)

        self.horizontalLayout.setStretch(0, 1)
        self.horizontalLayout.setStretch(1, 4)

        self.retranslateUi(ChartWidget)

        QMetaObject.connectSlotsByName(ChartWidget)
    # setupUi

    def retranslateUi(self, ChartWidget):
        ChartWidget.setWindowTitle(QCoreApplication.translate("ChartWidget", u"Form", None))
        self.btn_search_news.setText(QCoreApplication.translate("ChartWidget", u"\ub274\uc2a4 \uac80\uc0c9", None))
        self.label_3.setText(QCoreApplication.translate("ChartWidget", u"\ucc60\ud2b8\ud45c\uc2dc :", None))
        self.check_candle.setText(QCoreApplication.translate("ChartWidget", u"\uce94\ub4e4", None))
        self.check_heikin.setText(QCoreApplication.translate("ChartWidget", u"\ud558\uc774\ud0a8\uc544\uc2dc", None))
        self.label.setText(QCoreApplication.translate("ChartWidget", u"\uc774\ub3d9\ud3c9\uade0 : ", None))
        self.check_sma5.setText(QCoreApplication.translate("ChartWidget", u"5", None))
        self.check_sma10.setText(QCoreApplication.translate("ChartWidget", u"10", None))
        self.check_sma20.setText(QCoreApplication.translate("ChartWidget", u"20", None))
        self.check_sma60.setText(QCoreApplication.translate("ChartWidget", u"60", None))
        self.check_sma200.setText(QCoreApplication.translate("ChartWidget", u"200", None))
        self.label_2.setText(QCoreApplication.translate("ChartWidget", u"\ubcfc\ub9b0\uc838    :", None))
        self.check_bb10.setText(QCoreApplication.translate("ChartWidget", u"1.0", None))
        self.check_bb20.setText(QCoreApplication.translate("ChartWidget", u"2.0", None))
        self.check_bb30.setText(QCoreApplication.translate("ChartWidget", u"3.0", None))
    # retranslateUi

