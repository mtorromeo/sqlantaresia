from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QDialog, QFontDialog

from .Ui_SettingsDialog import Ui_SettingsDialog


class SettingsDialog(QDialog, Ui_SettingsDialog):
    def __init__(self, **kwds):
        super().__init__(**kwds)
        self.setupUi(self)

    def setEditorFont(self, font):
        self.lblSelectedFont.setFont(font)
        self.lblSelectedFont.setText("%s %d" % (font.family(), font.pointSize()))

    @pyqtSlot()
    def on_btnFont_clicked(self):
        fd = QFontDialog(self)
        if fd.exec_():
            self.setEditorFont(fd.selectedFont())
