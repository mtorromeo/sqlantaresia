from PyQt4.QtCore import Qt
from PyQt4.QtGui import QTabBar

class QMiddleClickCloseTabBar(QTabBar):
        def mouseReleaseEvent(self, event):
                if event.button() == Qt.MidButton:
                    self.tabCloseRequested.emit( self.tabAt( event.pos() ) )
                super(QTabBar, self).mouseReleaseEvent(event)