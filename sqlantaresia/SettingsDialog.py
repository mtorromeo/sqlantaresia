from PyQt4.QtCore import pyqtSignature
from PyQt4.QtGui import QDialog, QFontDialog

from Ui_SettingsDialog import Ui_SettingsDialog

class SettingsDialog(QDialog, Ui_SettingsDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)

    def setEditorFont(self, font):
        self.lblSelectedFont.setFont(font)
        self.lblSelectedFont.setText("%s %d" % (font.family(), font.pointSize()))

    @pyqtSignature("")
    def on_btnFont_clicked(self):
        fd = QFontDialog(self)
        if fd.exec_():
            self.setEditorFont(fd.selectedFont())