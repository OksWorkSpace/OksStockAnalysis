# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'RunModelDialog.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QDialog,
    QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QPlainTextEdit, QPushButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_RunModelDialog(object):
    def setupUi(self, RunModelDialog):
        if not RunModelDialog.objectName():
            RunModelDialog.setObjectName(u"RunModelDialog")
        RunModelDialog.resize(897, 505)
        self.verticalLayout = QVBoxLayout(RunModelDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.edit_np_path = QLineEdit(RunModelDialog)
        self.edit_np_path.setObjectName(u"edit_np_path")
        self.edit_np_path.setReadOnly(True)

        self.horizontalLayout.addWidget(self.edit_np_path)

        self.btn_np_path = QPushButton(RunModelDialog)
        self.btn_np_path.setObjectName(u"btn_np_path")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_np_path.sizePolicy().hasHeightForWidth())
        self.btn_np_path.setSizePolicy(sizePolicy)
        self.btn_np_path.setMinimumSize(QSize(100, 0))

        self.horizontalLayout.addWidget(self.btn_np_path)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.edit_darts_path = QLineEdit(RunModelDialog)
        self.edit_darts_path.setObjectName(u"edit_darts_path")
        self.edit_darts_path.setReadOnly(True)

        self.horizontalLayout_2.addWidget(self.edit_darts_path)

        self.btn_darts_path = QPushButton(RunModelDialog)
        self.btn_darts_path.setObjectName(u"btn_darts_path")
        sizePolicy.setHeightForWidth(self.btn_darts_path.sizePolicy().hasHeightForWidth())
        self.btn_darts_path.setSizePolicy(sizePolicy)
        self.btn_darts_path.setMinimumSize(QSize(100, 0))

        self.horizontalLayout_2.addWidget(self.btn_darts_path)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.check_np = QCheckBox(RunModelDialog)
        self.check_np.setObjectName(u"check_np")
        sizePolicy.setHeightForWidth(self.check_np.sizePolicy().hasHeightForWidth())
        self.check_np.setSizePolicy(sizePolicy)
        self.check_np.setMinimumSize(QSize(60, 0))

        self.horizontalLayout_3.addWidget(self.check_np)

        self.check_lgbm = QCheckBox(RunModelDialog)
        self.check_lgbm.setObjectName(u"check_lgbm")
        sizePolicy.setHeightForWidth(self.check_lgbm.sizePolicy().hasHeightForWidth())
        self.check_lgbm.setSizePolicy(sizePolicy)
        self.check_lgbm.setMinimumSize(QSize(60, 0))

        self.horizontalLayout_3.addWidget(self.check_lgbm)

        self.check_tft = QCheckBox(RunModelDialog)
        self.check_tft.setObjectName(u"check_tft")
        sizePolicy.setHeightForWidth(self.check_tft.sizePolicy().hasHeightForWidth())
        self.check_tft.setSizePolicy(sizePolicy)
        self.check_tft.setMinimumSize(QSize(60, 0))

        self.horizontalLayout_3.addWidget(self.check_tft)

        self.check_xgb = QCheckBox(RunModelDialog)
        self.check_xgb.setObjectName(u"check_xgb")
        sizePolicy.setHeightForWidth(self.check_xgb.sizePolicy().hasHeightForWidth())
        self.check_xgb.setSizePolicy(sizePolicy)
        self.check_xgb.setMinimumSize(QSize(60, 0))

        self.horizontalLayout_3.addWidget(self.check_xgb)

        self.check_re = QCheckBox(RunModelDialog)
        self.check_re.setObjectName(u"check_re")
        sizePolicy.setHeightForWidth(self.check_re.sizePolicy().hasHeightForWidth())
        self.check_re.setSizePolicy(sizePolicy)
        self.check_re.setMinimumSize(QSize(60, 0))

        self.horizontalLayout_3.addWidget(self.check_re)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer)

        self.btn_run_model = QPushButton(RunModelDialog)
        self.btn_run_model.setObjectName(u"btn_run_model")
        sizePolicy.setHeightForWidth(self.btn_run_model.sizePolicy().hasHeightForWidth())
        self.btn_run_model.setSizePolicy(sizePolicy)
        self.btn_run_model.setMinimumSize(QSize(100, 0))

        self.horizontalLayout_3.addWidget(self.btn_run_model)

        self.btn_stop_model = QPushButton(RunModelDialog)
        self.btn_stop_model.setObjectName(u"btn_stop_model")
        sizePolicy.setHeightForWidth(self.btn_stop_model.sizePolicy().hasHeightForWidth())
        self.btn_stop_model.setSizePolicy(sizePolicy)
        self.btn_stop_model.setMinimumSize(QSize(100, 0))

        self.horizontalLayout_3.addWidget(self.btn_stop_model)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.list_stocks = QListWidget(RunModelDialog)
        self.list_stocks.setObjectName(u"list_stocks")
        self.list_stocks.setEnabled(True)
        self.list_stocks.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.list_stocks.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.horizontalLayout_4.addWidget(self.list_stocks)

        self.text_output = QPlainTextEdit(RunModelDialog)
        self.text_output.setObjectName(u"text_output")
        self.text_output.setUndoRedoEnabled(False)
        self.text_output.setReadOnly(True)

        self.horizontalLayout_4.addWidget(self.text_output)

        self.horizontalLayout_4.setStretch(0, 1)
        self.horizontalLayout_4.setStretch(1, 4)

        self.verticalLayout.addLayout(self.horizontalLayout_4)


        self.retranslateUi(RunModelDialog)

        QMetaObject.connectSlotsByName(RunModelDialog)
    # setupUi

    def retranslateUi(self, RunModelDialog):
        RunModelDialog.setWindowTitle(QCoreApplication.translate("RunModelDialog", u"\uc8fc\uac00 \uc608\uce21 \ubaa8\ub378 \ub2e4\uc774\uc5bc\ub85c\uadf8", None))
        self.btn_np_path.setText(QCoreApplication.translate("RunModelDialog", u"NP \ubaa8\ub378 \uacbd\ub85c", None))
        self.btn_darts_path.setText(QCoreApplication.translate("RunModelDialog", u"Darts \ubaa8\ub378 \uacbd\ub85c", None))
        self.check_np.setText(QCoreApplication.translate("RunModelDialog", u"NP", None))
        self.check_lgbm.setText(QCoreApplication.translate("RunModelDialog", u"LGBM", None))
        self.check_tft.setText(QCoreApplication.translate("RunModelDialog", u"TFT", None))
        self.check_xgb.setText(QCoreApplication.translate("RunModelDialog", u"XGB", None))
        self.check_re.setText(QCoreApplication.translate("RunModelDialog", u"RE", None))
        self.btn_run_model.setText(QCoreApplication.translate("RunModelDialog", u"\uc2e4\ud589\ud558\uae30", None))
        self.btn_stop_model.setText(QCoreApplication.translate("RunModelDialog", u"\uc911\uc9c0\ud558\uae30", None))
    # retranslateUi

