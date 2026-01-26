#Written by MaskPlauge
import winreg
import os
import mobase
import socket
import json
import threading

try:
    from PyQt6.QtWidgets import (QMessageBox, QMainWindow, QTabWidget, QWidget, QTreeView, QStyle, 
                                 QStyledItemDelegate, QStyleOptionViewItem, QStyleOptionProgressBar, 
                                 QApplication, QPushButton)
    from PyQt6.QtCore import Qt, QModelIndex, QObject, pyqtSignal, QAbstractItemModel
except:
    from PyQt5.QtWidgets import (QMessageBox, QMainWindow, QTabWidget, QWidget, QTreeView, QStyle, 
                                 QStyledItemDelegate, QStyleOptionViewItem, QStyleOptionProgressBar, 
                                 QApplication, QPushButton)
    from PyQt5.QtCore import Qt, QModelIndex, QObject, pyqtSignal, QAbstractItemModel

SIZE_COLUMN = 2
STATUS_COLUMN = 1
FILENAME_COLUMN = 0
PROTOCOL = "mws-mo2"

class ProgressListener(QObject):
    # filename, current_bytes, total_bytes
    progress_received = pyqtSignal(str, int, int)

    def __init__(self):
        super().__init__()
        self.running = True
        self.server_socket = None
        self.thread = threading.Thread(target=self.run_server, daemon=True)
        self.thread.start()

    def run_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('127.0.0.1', 0))
            #Get socket for EXE to read from registry
            port = self.server_socket.getsockname()[1]
            base = winreg.HKEY_CURRENT_USER
            key = winreg.OpenKey(base, fr"Software\Classes\{PROTOCOL}", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "port", 0, winreg.REG_SZ, str(port))
            winreg.CloseKey(key)

            self.server_socket.listen(5)
            print(f"Plugin listening on port {port}")

            while self.running:
                client, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()
        except Exception as e:
            print(f"Socket server error: {e}")

    def handle_client(self, conn):
        with conn:
            buffer = ""
            connected = True
            while connected:
                try:
                    data = conn.recv(1024)
                    if not data:
                        break
                    buffer += data.decode('utf-8')
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        try:
                            msg = json.loads(line)
                            self.progress_received.emit(msg['file'], msg['cur'], msg['max'])
                        except json.JSONDecodeError:
                            pass
                except:
                    connected = False

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()

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
        data = self.data_holder.data.get(file_name, None)
        if data is not None:
            # --- DRAW CUSTOM PROGRESS BAR ---
            progress_value = data["progress"]
            max_value = data["total"]
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

class Data_Holder():
    model:QAbstractItemModel = None
    view:QTreeView = None
    refresh:QPushButton.click = None
    data = {}

class mws_protocol_register(mobase.IPlugin):
    def name(self):
        return "MWS-MO2 Protocol Register"
    
    def author(self):
        return "MaskPlague"
    
    def version(self):
        return mobase.VersionInfo(1, 0, 0)

    def init(self, organizer):
        self._organizer = organizer
        self._register_protocol()
        self._organizer.modList().onModInstalled(self._mod_installed)
        self._organizer.onUserInterfaceInitialized(self._get_downloads)
        self.main_window = None
        self.new_delegate = None
        self.data_holder:Data_Holder = Data_Holder()
        self.listener = ProgressListener()
        self.listener.progress_received.connect(self.on_external_progress)
        self._organizer.modList().onModStateChanged(lambda x: self.on_external_progress("Animated Payday 3 Loading Screens.zip", 100, 7800000))
        return True
    
    def on_external_progress(self, file_name, progress, total):
        #If total is -1 the download is complete
        if total == -1:
            self.data_holder.data.pop(file_name)
            self.data_holder.refresh()
            return
        
        model = self.data_holder.model
        if model is None:
            return
        
        start_index = model.index(0, FILENAME_COLUMN)
        matching_indexes = model.match(
            start_index, 
            Qt.ItemDataRole.DisplayRole, 
            file_name, 
            1,
            Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchWrap
        )

        if matching_indexes:
            index_name = matching_indexes[0]
            row = index_name.row()
            index_status = model.index(row, STATUS_COLUMN)
            self.data_holder.data.update({file_name: {"progress": progress, "total": total}})
            self.data_holder.view.update(index_status)
        
        return

    def _get_downloads(self, main_window: QMainWindow):
        if self.main_window is None:
            self.main_window = main_window
        tabWidget = main_window.findChild(QTabWidget, "tabWidget")
        downloadTab = tabWidget.findChild(QWidget, "downloadTab")
        self.data_holder.refresh = downloadTab.findChild(QPushButton, "btnRefreshDownloads").click
        downloadView = downloadTab.findChild(QTreeView, "downloadView")

        current_delegate = downloadView.itemDelegate()
        if not isinstance(current_delegate, HybridDownloadDelegate):
            self.new_delegate = HybridDownloadDelegate(current_delegate, self.data_holder, downloadView)
            downloadView.setItemDelegateForColumn(STATUS_COLUMN, self.new_delegate)
            self.data_holder.view = downloadView
            self.data_holder.model = downloadView.model()

    def _mod_installed(self, mod:mobase.IModInterface):
        if mod.repository() == "ModWorkshop":
            mod.setUrl(f"https://modworkshop.net/mod/{mod.nexusId()}")

    def _register_protocol(self):
        download_dir = self._organizer.downloadsPath()
        self_path = os.path.join(os.path.split(self._organizer.getPluginDataPath())[0], 'MWS Handler')

        # The path to the MWS link handler executable
        exe_path = exe_path = os.path.abspath(os.path.join(self_path, 'MWS_Link_Handler.exe'))
        command = f'"{exe_path}" "{download_dir}" "%1"'

        # MO2 path passed for launching if the program is not open
        mo2_path = os.path.join(*os.path.normpath(self_path).split(os.sep)[:3], 'ModOrganizer.exe')
        try:
            # Use CURRENT_USER instead of CLASSES_ROOT to avoid needing admin
            base = winreg.HKEY_CURRENT_USER

            key = winreg.CreateKey(base, fr"Software\Classes\{PROTOCOL}")
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ, fr"URL:{PROTOCOL.upper()} Protocol")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            winreg.SetValueEx(key, 'mo_path', 0, winreg.REG_SZ, fr"{mo2_path}")
            winreg.SetValueEx(key, 'port', 0, winreg.REG_SZ, "-1")

            # Set the command for shell\open\command
            subkey = winreg.CreateKey(key, r"shell\open\command")
            winreg.SetValueEx(subkey, None, 0, winreg.REG_SZ, command)
            winreg.CloseKey(key)

            print(f"Registered protocol '{PROTOCOL}' with handler: {command}")
            self._organizer.setPluginSetting(self.name(), f"{PROTOCOL.upper()} Protocol Registered", True)

        except Exception as e:
            print(f"Failed to register protocol: {e}")
            self._organizer.setPluginSetting(self.name(), f"{PROTOCOL.upper()} Protocol Registered", False)
            QMessageBox.warning(None, f"{PROTOCOL.upper()} Protocol Register Failed", f"Failed to regester protocol to the registry for {PROTOCOL.upper()} links (ModWorkshop.net)")

    def settings(self):
        return [
            mobase.PluginSetting(f"{PROTOCOL.upper()} Protocol Registered", f"Indicates if {PROTOCOL.upper()} links are handled, changing this does nothing.", False)
            ]
    
    def description(self):
        return f"Registers the {PROTOCOL.upper()} protocol to handle downloads."
    