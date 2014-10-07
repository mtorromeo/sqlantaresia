from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTabBar


class QMiddleClickCloseTabBar(QTabBar):
        def mouseReleaseEvent(self, event):
                if event.button() == Qt.MidButton:
                    self.tabCloseRequested.emit(self.tabAt(event.pos()))
                super(QTabBar, self).mouseReleaseEvent(event)
