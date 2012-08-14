# -*- coding: utf-8 -*-

from PyQt4.QtGui import QTreeView, QHeaderView


class DbTreeView(QTreeView):
    def setModel(self, model):
        oldModel = self.model()
        if oldModel:
            oldModel.dataChanged.disconnect(self.adaptColumns)
            oldModel.modelReset.connect(self.adaptColumns)

        model.dataChanged.connect(self.adaptColumns)
        model.modelReset.connect(self.adaptColumns)

        return QTreeView.setModel(self, model)

    def adaptColumns(self, topLeft=None, bottomRight=None):
        self.header().setResizeMode(0, QHeaderView.Stretch)
        self.header().setResizeMode(1, QHeaderView.ResizeToContents)
