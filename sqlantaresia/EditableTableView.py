# -*- coding: utf-8 -*-
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QTableView, QAbstractItemView


class EditableTableView(QTableView):
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and self.state() != QAbstractItemView.EditingState:
            selected = self.selectionModel().selectedIndexes()
            if selected:
                selected = selected[0]
                self.setCurrentIndex(selected)
                self.edit(selected)
        else:
            QTableView.keyPressEvent(self, event)
