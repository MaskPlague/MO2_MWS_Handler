#Written by MaskPlague

from urllib.request import urlopen

from .data_holder import Data_Holder
from ..globals import *

try:
    from PyQt6.QtWidgets import (QStyle, QStyledItemDelegate, QStyleOptionViewItem,
                                  QStyleOptionProgressBar, QApplication)
    from PyQt6.QtCore import Qt, QModelIndex
except ImportError:
    from PyQt5.QtWidgets import (QStyle, QStyledItemDelegate, QStyleOptionViewItem,  # type: ignore
                                 QStyleOptionProgressBar, QApplication)
    from PyQt5.QtCore import Qt, QModelIndex # type: ignore

class HybridDownloadDelegate(QStyledItemDelegate):
    def __init__(self, original_delegate, data_holder, parent=None):
        super().__init__(parent)
        self.original_delegate = original_delegate
        self.data_holder:Data_Holder = data_holder

    def format_bytes(self, size_bytes):
        if size_bytes >= 1024**3:
            size_gb = size_bytes / (1024**3)
            return f"{size_gb:.2f} GB"
        elif size_bytes >= 1024**2:
            size_mb = size_bytes / (1024**2)
            return f"{size_mb:.2f} MB"
        elif size_bytes >= 1024:
            size_kb = size_bytes / 1024
            return f"{size_kb:.2f} KB"
        else:
            return f"{size_bytes} Bytes"
        
    def paint(self, painter, option: QStyleOptionViewItem, index: QModelIndex):
        file_name = self.data_holder.model.index(index.row(), 0).data(Qt.ItemDataRole.DisplayRole)
        data = self.data_holder.data.get(file_name)
        if data is not None:
            # --- DRAW CUSTOM PROGRESS BAR ---
            progress_value = data["progress"]
            max_value = data["total"]
            if data["cancelled"]:
                option.text = "Cancelling"
                QApplication.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, option, painter)
                return
            if max_value <= 0:
                return
            total_size = self.format_bytes(max_value)
            # Setup the style option for a progress bar
            progress_opt = QStyleOptionProgressBar()
            progress_opt.rect = option.rect
            progress_opt.minimum = 0
            progress_opt.maximum = max_value
            progress_opt.progress = int(progress_value)
            progress_opt.text = f"{int((progress_value / max_value) * 100)}% of {total_size}"
            progress_opt.textVisible = True
            progress_opt.textAlignment = Qt.AlignmentFlag.AlignCenter

            QApplication.style().drawControl(QStyle.ControlElement.CE_ProgressBar, progress_opt, painter)
        else:
            # --- PASS TO ORIGINAL ---
            if self.original_delegate:
                self.original_delegate.paint(painter, option, index)
            else:
                super().paint(painter, option, index)