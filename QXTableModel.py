from PyQt4.QtSql import QSqlTableModel
from PyQt4.QtCore import SIGNAL

class QXTableModel(QSqlTableModel):
	def __init__(self, parent, db):
		QSqlTableModel.__init__(self, parent, db)
	
	def submit(self):
		result = QSqlTableModel.submit(self)
		self.emit(SIGNAL("edited"))
		return result
