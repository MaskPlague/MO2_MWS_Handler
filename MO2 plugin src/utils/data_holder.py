#Written by MaskPlague
try:
    from PyQt6.QtCore import QAbstractItemModel
    from PyQt6.QtWidgets import QTreeView
except ImportError:
    from PyQt5.QtCore import QAbstractItemModel
    from PyQt5.QtWidgets import QTreeView

class Data_Holder():
    def __init__(self):
        self.model:QAbstractItemModel = None
        self.view:QTreeView = None
        self.data:dict = {}

    def refresh(self):
        pass