from PyQt4.QtGui import QMessageBox
from PyQt4.QtSql import QSqlDatabase, QSqlDriver, QSqlQuery

class IdeSqlDatabase(QSqlDatabase):
	def __init__(self, db):
		QSqlDatabase.__init__(self, db)

	def escapeTableName(self, tableName):
		return self.driver().escapeIdentifier(tableName, QSqlDriver.TableName)

	def confirmQuery(self, sql, query=None):
		if QMessageBox.question(QApplication.activeWindow(), "Query confirmation request", "%s\nAre you sure?" % sql, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
			if query is None:
				query = QSqlQuery( sql, self )
			if not query.exec_() and query.lastError().isValid():
				QMessageBox.critical(QApplication.activeWindow(), "Query result", query.lastError().databaseText())
