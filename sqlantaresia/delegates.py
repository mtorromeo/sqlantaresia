from PyQt4.QtGui import QItemDelegate, QDateEdit, QTimeEdit, QDateTimeEdit
from PyQt4.QtCore import Qt, QDate, QTime, QDateTime


class CustomDelegate(QItemDelegate):
    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        self.setEditorValue(editor, value)

    def setModelData(self, editor, model, index):
        model.setData(index, self.setModelValue(editor), Qt.EditRole)


class DateDelegate(CustomDelegate):
    def createEditor(self, parent, option, index):
        editor = QDateEdit(parent)
        editor.setCalendarPopup(True)
        return editor

    def setEditorValue(self, editor, value):
        editor.setDate(QDate.fromString(value, "yyyy-MM-dd"))

    def setModelValue(self, editor):
        return editor.date().toString("yyyy-MM-dd")


class DateTimeDelegate(CustomDelegate):
    def createEditor(self, parent, option, index):
        editor = QDateTimeEdit(parent)
        editor.setCalendarPopup(True)
        return editor

    def setEditorValue(self, editor, value):
        editor.setDateTime(QDateTime.fromString(value, "yyyy-MM-dd HH:mm:ss"))

    def setModelValue(self, editor):
        return editor.dateTime().toString("yyyy-MM-dd HH:mm:ss")


class TimeDelegate(CustomDelegate):
    def createEditor(self, parent, option, index):
        return QTimeEdit(parent)

    def setEditorValue(self, editor, value):
        editor.setTime(QTime.fromString(value, "HH:mm:ss"))

    def setModelValue(self, editor):
        return editor.time().toString("HH:mm:ss")
