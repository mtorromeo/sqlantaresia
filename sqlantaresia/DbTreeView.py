# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QTreeView, QHeaderView


class DbTreeView(QTreeView):
    def setModel(self, model):
        oldModel = self.model()
        if oldModel:
            oldModel.dataChanged.disconnect()
            oldModel.modelReset.disconnect()

        model.dataChanged.connect(self.adaptColumns)
        model.modelReset.connect(self.adaptColumns)

        return QTreeView.setModel(self, model)

    def adaptColumns(self, topLeft=None, bottomRight=None):
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
