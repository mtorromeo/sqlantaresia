# -*- coding: utf-8 -*-
from PyQt4.QtGui import QTabWidget, QSpacerItem, QSizePolicy, QFileDialog
from PyQt4.QtCore import pyqtSignature, pyqtSignal

from Ui_DumpWidget import Ui_DumpWidget

import re
import datetime
import application
import MySQLdb

from zipfile import ZipFile
from gzip import GzipFile
from bz2 import BZ2File

from connections import QueryThread
from _mysql_exceptions import Error as MySQLError


class DumpTab(QTabWidget, Ui_DumpWidget):
    def __init__(self, connection, dbName):
        QTabWidget.__init__(self)

        self.connection = connection
        self.dbName = dbName

        self.setupUi(self)
        self.groupProgress.setVisible(False)

    @pyqtSignature("")
    def on_btnSave_clicked(self):
        extension = ".sql"
        compression = ""

        if self.radioZip.isChecked():
            compression = "zip"
        elif self.radioGzip.isChecked():
            compression = "gz"
        elif self.radioBzip2.isChecked():
            compression = "bz2"

        if compression:
            extension += "." + compression

        fileName = QFileDialog.getSaveFileName(self, "Save database dump", "", "SQL Files (*%s)" % extension)
        if not fileName:
            return

        self.groupProgress.setVisible(True)
        self.groupSchema.setEnabled(False)
        self.groupData.setEnabled(False)
        self.groupCompression.setEnabled(False)

        limitDumpData = self.spinLimit.value() if self.chkLimit.isChecked() else None

        self.thread = DumpThread(self.connection, self.dbName, fileName,
                                 compression, dumpSchema=self.groupSchema.isChecked(),
                                 dumpData=self.groupData.isChecked(), dumpTables=self.chkTables.isChecked(),
                                 dumpViews=self.chkViews.isChecked(), dumpTriggers=self.chkTriggers.isChecked(),
                                 limitDumpData=limitDumpData)
        self.thread.progress.connect(self.on_dumpProgress)
        self.thread.subProgress.connect(self.on_dumpSubProgress)
        self.thread.query_terminated.connect(self.on_dumpTerminated)
        self.thread.start()

    def on_dumpProgress(self, step, steps, statusMessage):
        self.mainProgressBar.setFormat(statusMessage + " (%p%)")
        self.mainProgressBar.setMaximum(steps)
        self.mainProgressBar.setValue(step)

    def on_dumpSubProgress(self, step, steps, statusMessage):
        self.subProgressBar.setFormat(statusMessage + " (%p%)")
        self.subProgressBar.setMaximum(steps)
        self.subProgressBar.setValue(step)

    def on_dumpTerminated(self, thread):
        self.groupProgress.setVisible(False)
        self.mainProgressBar.setFormat("%p%")
        self.mainProgressBar.setValue(0)
        self.subProgressBar.setFormat("%p%")
        self.subProgressBar.setValue(0)
        self.groupSchema.setEnabled(True)
        self.groupData.setEnabled(True)
        self.groupCompression.setEnabled(True)


class DumpThread(QueryThread):
    progress = pyqtSignal(int, int, str)
    subProgress = pyqtSignal(int, int, str)

    def __init__(self, connection, db, destfile, compression, dumpSchema, dumpData, dumpTables,
                 dumpViews, dumpTriggers, limitDumpData):
        QueryThread.__init__(self, connection=connection, db=db, query="")
        self.destfile = destfile
        self.compression = compression
        self.dumpSchema = dumpSchema
        self.dumpData = dumpData
        self.dumpTables = dumpSchema and dumpTables
        self.dumpViews = dumpSchema and dumpViews
        self.dumpTriggers = dumpSchema and dumpTriggers
        self.limitDumpData = limitDumpData
        self.step = 0
        self.steps = 0

    def advance(self, message):
        self.step += 1
        self.progress.emit(self.step, self.steps, message)

    def dbworker(self):
        quoteDbName = self.connection.quoteIdentifier(self.db)
        self.progress.emit(0, 100, "Starting...")

        if self.compression == "":
            opener = open
        elif self.compression == "zip":
            opener = ZipFile
        elif self.compression == "gz":
            opener = GzipFile
        elif self.compression == "bz2":
            opener = BZ2File

        with opener(self.destfile, "w") as f:

            try:
                cursor = self.connection.cursor()

                cursor.execute("SHOW FULL TABLES IN %s WHERE Table_type='BASE TABLE'" % quoteDbName)
                tables = [row[0] for row in cursor.fetchall()]

                self.steps = 1
                if self.dumpTables:
                    self.steps += len(tables)

                if self.dumpViews:
                    cursor.execute("SHOW FULL TABLES IN %s WHERE Table_type='VIEW'" % quoteDbName)
                    views = [row[0] for row in cursor.fetchall()]
                    self.steps += len(views)
                else:
                    views = []

                cursor.execute("SHOW VARIABLES LIKE 'version';")
                row = cursor.fetchone()
                serverVersion = row[1]

                f.write("""-- {appName} {appVersion}
--
-- Host: {host}    Database: {db}
-- ------------------------------------------------------
-- Server version       {serverVersion}

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;""".format(
    appName=application.name,
    appVersion=application.version,
    host=self.connection.host,
    db=self.db,
    serverVersion=serverVersion,
))

                for table in tables:
                    quoteTable = self.connection.quoteIdentifier(table)
                    self.advance("Dumping table %s" % table)

                    if self.dumpTables:
                        cursor.execute("SHOW CREATE TABLE %s.%s;" % (quoteDbName, quoteTable))
                        row = cursor.fetchone()
                        create = row[1]

                        f.write("""

--
-- Table structure for table {table}
--

DROP TABLE IF EXISTS {table};
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
{create};
/*!40101 SET character_set_client = @saved_cs_client */;""".format(
    table=quoteTable,
    create=create,
))

                    if self.dumpTriggers:
                        query = "SHOW TRIGGERS IN %s WHERE `Table` = ?;" % (quoteDbName,)
                        cursor.execute(query.replace("?", "%s"), (table,))

                        triggers = cursor.fetchall()
                        for trigger in triggers:
                            definer = trigger[7].split('@', 2)
                            f.write("""/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = '' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER={definer}@{definerHost}*/ /*!50003 TRIGGER {trigger} {timing} {event} ON {table}
FOR EACH ROW {statement} */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;""".format(
    trigger=self.connection.quoteIdentifier(trigger[0]),
    definer=self.connection.quoteIdentifier(definer[0]),
    definerHost=self.connection.quoteIdentifier(definer[1]),
    table=quoteTable,
    statement=trigger[3],
    timing=trigger[4],
    event=trigger[1],
))

                    if self.dumpData:
                        cursor.execute("SELECT COUNT(*) FROM %s.%s;" % (quoteDbName, quoteTable))
                        count = cursor.fetchone()[0]
                        if self.limitDumpData:
                            count = min(count, self.limitDumpData)

                        if count:
                            self.subProgress.emit(0, count, "Dumping rows of table %s" % quoteTable)

                            f.write("""

--
-- Dumping data for table {table}
--

LOCK TABLES {table} WRITE;
/*!40000 ALTER TABLE {table} DISABLE KEYS */;
INSERT INTO {table} VALUES """.format(table=quoteTable))

                            limit = " LIMIT %d" % self.limitDumpData if self.limitDumpData else ""
                            rownum = 0
                            for row in self.connection.iterall("SELECT * FROM %s.%s%s;" % (quoteDbName, quoteTable, limit), cursor=cursor):
                                rownum += 1

                                datarow = []
                                for i, cell in enumerate(row):
                                    if cell is None:
                                        datarow.append("NULL")
                                    elif cursor.description[i][1] in MySQLdb.BINARY:
                                        if type(cell) is unicode:
                                            cell = cell.encode("utf-8")
                                        datarow.append("0x%s" % cell.encode("hex"))
                                    elif isinstance(cell, basestring):
                                        try:
                                            datarow.append("'%s'" % self.connection.escapeString(cell.encode("utf-8")))
                                        except UnicodeDecodeError:
                                            datarow.append("0x%s" % cell.encode("utf-8").encode("hex"))
                                    elif isinstance(cell, (int, long, float)):
                                        datarow.append(str(cell))
                                    else:
                                        datarow.append("'%s'" % self.connection.escapeString(str(cell)))

                                if row > 0:
                                    f.write(", ")
                                f.write("(%s)" % ",".join(datarow))

                                self.subProgress.emit(rownum, count, "Dumping rows of table %s" % quoteTable)

                            f.write(""";
/*!40000 ALTER TABLE {table} ENABLE KEYS */;
UNLOCK TABLES;
""".format(table=quoteTable))

                if self.dumpViews:
                    for view in views:
                        view = self.connection.quoteIdentifier(view)
                        self.advance("Dumping view %s" % view)

                        cursor.execute("SHOW CREATE VIEW %s.%s;" % (quoteDbName, view))
                        row = cursor.fetchone()

                        create = re.sub("^(CREATE ALGORITHM=[^ ]+ )(DEFINER=[^ ]+ SQL SECURITY [^ ]+ )",
                                        "/*!50001 \\1*/\n/*!50013 \\2*/\n", row[1])

                        f.write("""

--
-- View structure for view {view}
--

/*!50001 DROP TABLE IF EXISTS {view}*/;
/*!50001 DROP VIEW IF EXISTS {view}*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
{create};
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;;
""".format(
    view=view,
    create=create,
))

                self.advance("Dump terminated")

            except MySQLError as (errno, errmsg):  # @UnusedVariable
                print errmsg

            f.write("""
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on %s\n""" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
