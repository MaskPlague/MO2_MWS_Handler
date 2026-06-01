#Written by MaskPlague
import winreg
import socket
import json
import threading

from ..globals import *
from .data_holder import Data_Holder

try:
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:
    from PyQt5.QtCore import QObject, pyqtSignal # type: ignore

class ProgressListener(QObject):
    # filename, current_bytes, total_bytes
    progress_received = pyqtSignal(str, int, int)

    def __init__(self, data_holder: Data_Holder):
        super().__init__()
        self.running = True
        self.server_socket = None
        self.thread = threading.Thread(target=self.run_server, daemon=True)
        self.thread.start()
        self.active_sockets:dict = {}
        self.data_holder = data_holder

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

    def handle_client(self, conn: socket.socket):
        current_filename  = None
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
                            file_name = msg['file']
                            progress = msg['cur']
                            total = msg['max']
                            if current_filename is None:
                                current_filename = file_name
                                self.active_sockets[file_name] = conn
                            self.progress_received.emit(file_name, progress, total)

                            if total == -1 or total == progress:
                                if current_filename in self.active_sockets:
                                    self.active_sockets.pop(current_filename)

                        except json.JSONDecodeError:
                            pass
                except Exception as e:
                    connected = False
                    if current_filename is not None:
                        self.progress_received.emit(current_filename, -1, -1)

    def cancel_download(self, file_name):
        if file_name in self.active_sockets:
            try:
                print(f"Sending cancel command for {file_name}")
                conn: socket.socket = self.active_sockets.pop(file_name)
                
                # Send the cancel command
                cmd = json.dumps({"action": "cancel"}) + "\n"
                conn.sendall(cmd.encode('utf-8'))
                data = self.data_holder.data.get(file_name)
                if data:
                    self.data_holder.data.update(
                        {file_name: {"progress": data["progress"], 
                                     "total": data["total"], 
                                     "cancelled": True}})
                    self.data_holder.view.update()
            except Exception as e:
                print(f"Failed to send cancel: {e}")

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()