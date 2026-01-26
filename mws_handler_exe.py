import sys
import os
import psutil
import winreg
import threading
import json
import socket

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QLabel

from urllib.request import urlretrieve
from urllib.request import urlopen
from urllib.parse import unquote

#Compile command: pyinstaller mws_handler_exe.py --onefile -n MWS_Link_Handler --noconsole
PROTOCOL = "mws-mo2"

class mws_handler():
    def __init__(self):   
        self.mod_name = "Unknown"
        self.file_version = "0.0.0.0"
        self.mod_version = "0.0.0.0"
        self.mod_last_updated = "2000-0-0T0"
        self.file_last_updated = "2000-0-0T0"

    def main(self):
        if len(sys.argv) > 2:
            download_location = sys.argv[1]
            link = sys.argv[2]
            split = link.split('/')
            file_id = split[-1]
            mod_id = split[-2]
            game_id = split[-3]
            download_link = f"https://api.modworkshop.net/files/{file_id}/download"

            try:
                base = winreg.HKEY_CURRENT_USER
                key = winreg.OpenKey(base, fr"Software\Classes\{PROTOCOL}")
                last_game = winreg.QueryValueEx(key, 'game')[0]
                winreg.CloseKey(key)
            except:
                last_game = "MWS_None"

            if last_game != "None" and last_game != game_id:
                self.show_message(f'Download is for "{game_id}" but, the last opened instance is for "{last_game}".', 5000)
                return
            
            response = urlopen(download_link)
            filename = unquote(response.headers.get_filename())
            response.close()

            available_name = self.get_available_name(download_location, filename)
            download_path = os.path.join(download_location, available_name)
            if not self.is_mo2_running():
                try:
                    base = winreg.HKEY_CURRENT_USER
                    key = winreg.OpenKey(base, fr"Software\Classes\{PROTOCOL}")
                    mo2_path = winreg.QueryValueEx(key, 'mo_path')[0]
                    winreg.CloseKey(key)
                    if os.path.exists(mo2_path):
                        os.startfile(mo2_path)
                except:
                    pass

            download_thread = threading.Thread(target=self.download_file, args=(download_link, download_path, available_name))
            download_thread.start()
            self.show_message('Download Started', 1500)

            name_thread = threading.Thread(target=self.get_mod_name_from_api, args=(mod_id,))
            name_thread.start()

            file_version_thread = threading.Thread(target=self.get_file_version_and_date_from_api, args=(file_id,))
            file_version_thread.start()

            mod_version_thread = threading.Thread(target=self.get_mod_version_from_api, args=(mod_id,))
            mod_version_thread.start()

            file_version_thread.join()
            mod_version_thread.join()
            name_thread.join()
            
            if self.mod_version.strip() == "" or self.file_version.strip() == "":
                self.get_latest_file_date_from_api(mod_id)
                self.mod_version = self.convert_time_to_version(self.mod_last_updated)
                self.file_version = self.convert_time_to_version(self.file_last_updated)

            download_metadata = os.path.join(download_location, available_name + '.meta')
            with open(download_metadata, 'w', encoding='utf-8') as f:
                f.write("[General]\n"+
                        "removed=false\n"+
                        f"gameName={game_id}\n"+
                        f"modID={mod_id}\n"+
                        f"fileID={file_id}\n"+
                        f"url=https://modworkshop.net/mod/{mod_id}\n"+
                        f"hasCustomUrl=true\n"+
                        f"name={os.path.splitext(filename)[0]}\n"+
                        "description=\n"+
                        f"modName={self.mod_name}\n"+
                        f"version={self.file_version}\n"+
                        f"newestVersion={self.mod_version}\n"+
                        f"fileTime=@DateTime({r'\0\0\0\x10\0\x80\0\0\0\0\0\0\0\xff\xff\xff\xff\0'})\n"+
                        "fileCategory=0\n"+
                        "category=0\n"+
                        "repository=ModWorkshop\n"+
                        f"userData=@Variant({r'\0\0\0\b\0\0\0\0'})\n"+
                        "installed=false\n"+
                        "uninstalled=false\n"+
                        "paused=false")
                f.close()
            download_thread.join()

    def download_file(self, download_link, download_path, filename):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connected = False
        
        def try_connect():
            nonlocal sock
            nonlocal connected
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                base = winreg.HKEY_CURRENT_USER
                key = winreg.OpenKey(base, fr"Software\Classes\{PROTOCOL}")
                port = int(winreg.QueryValueEx(key, 'port')[0])
                winreg.CloseKey(key)
                if port != -1:
                    sock.connect(('127.0.0.1', port))
                    connected = True
            except ConnectionRefusedError:
                connected = False
            except Exception as e:
                print(e)
                connected = False

        try_connect()

        def progress_hook(block_num, block_size, total_size):
            nonlocal sock
            nonlocal connected
            try:
                if connected:
                    current_downloaded = block_num * block_size
                    msg = {
                        "file": filename,
                        "cur": current_downloaded,
                        "max": total_size
                    }
                    sock.sendall((json.dumps(msg) + "\n").encode('utf-8'))
                else:
                    raise ConnectionError("Not connected")
            except:
                if connected:
                    try:
                        sock.close()
                    except:
                        pass
                    connected = False
                try_connect()

        try:
            urlretrieve(download_link, download_path, reporthook=progress_hook)
            
            if connected:
                msg = {"file": filename, "cur": -1, "max": -1}
                sock.sendall((json.dumps(msg) + "\n").encode('utf-8'))
        finally:
            try:
                sock.close()
            except:
                pass

    def convert_time_to_version(self, time:str):
        return "d" + time.split("T")[0].replace('-', '.')

    def get_mod_name_from_api(self, mod_id):
        mod_name_link = f"https://api.modworkshop.net/mods/{mod_id}"
        try:
            response = urlopen(mod_name_link)
            json_data:dict = json.load(response)
            response.close()
            self.mod_name = json_data.get("name", mod_id)
        except:
            self.mod_name = mod_id
    
    def get_latest_file_date_from_api(self, mod_id):
        mod_name_link = f"https://api.modworkshop.net/mods/{mod_id}/files/latest"
        try:
            response = urlopen(mod_name_link)
            json_data:dict = json.load(response)
            response.close()
            self.mod_last_updated = json_data.get("updated_at", "2000-0-0T0")
        except:
            self.mod_last_updated = "2000-0-0T0"
            pass

    def get_file_version_and_date_from_api(self, file_id):
        file_version_link = f"https://api.modworkshop.net/files/{file_id}"
        try:
            response = urlopen(file_version_link)
            json_data:dict = json.load(response)
            response.close()
            self.file_version = json_data.get("version", "")
            self.file_last_updated = json_data.get("updated_at", "2000-0-0T0")
        except:
            self.file_version = ""
            self.file_last_updated = "2000-0-0T0"

    def get_mod_version_from_api(self, mod_id):
        mod_version_link = f"https://api.modworkshop.net/mods/{mod_id}/version"
        try:
            response = urlopen(mod_version_link)
            self.mod_version = response.read().decode('utf-8')
            response.close()
        except:
            self.mod_version = ""

    def get_available_name(self, download_location, name, number = 0):
        if number == 0:
            new_name = name
        else:
            split = os.path.splitext(name)
            new_name = split[0] + '(' + str(number) + ')' + split[1]
        
        download_path = os.path.join(download_location, new_name)
        
        try:
            with open(download_path, 'x') as f:
                pass
            return new_name
        except:
            return self.get_available_name(download_location, name, number+1)
        
    def is_mo2_running(self):
        for process in psutil.process_iter(['name']):
            if process.info['name'] == 'ModOrganizer.exe':
                return True
        return False
    
    #Jump through hoops to launch MO2 without allowing it access to pyInstaller's temp _MEI folder
    #If MO2 touches the _MEI folder than once the download finishes pyInstaller will try to delete the temp _MEI folder
    #but MO2 will be locking the MSVC dlls and it will give an error about not being able to delete the temp _MEI folder
    def open_mo2_if_not_running(self):
        if not self.is_mo2_running():
            try:
                base = winreg.HKEY_CURRENT_USER
                key = winreg.OpenKey(base, fr"Software\Classes\{PROTOCOL}")
                mo2_path = winreg.QueryValueEx(key, 'mo_path')[0]
                winreg.CloseKey(key)
                if os.path.exists(mo2_path):
                    LAUNCH_PROTOCOL = "mws-mo2-force-launch"
                
                    proto_key = winreg.CreateKey(base, fr"Software\Classes\{LAUNCH_PROTOCOL.upper()}")
                    winreg.SetValueEx(proto_key, None, 0, winreg.REG_SZ, f"URL:{LAUNCH_PROTOCOL.upper()} Protocol")
                    winreg.SetValueEx(proto_key, "URL Protocol", 0, winreg.REG_SZ, "")
                    
                    cmd_key = winreg.CreateKey(proto_key, r"shell\open\command")
                    
                    winreg.SetValueEx(cmd_key, None, 0, winreg.REG_SZ, fr'"{mo2_path}"')
                    
                    winreg.CloseKey(cmd_key)
                    winreg.CloseKey(proto_key)

                    command = f'explorer "{LAUNCH_PROTOCOL}://none/"'
                    subprocess.run(command, shell=True, check=False, close_fds=True, creationflags=subprocess.DETACHED_PROCESS)
            except:
                pass

    def show_message(self, msg, duration=2000):
        app = QApplication([])
        label = QLabel(msg)
        label.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool |
                            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.X11BypassWindowManagerHint)
        label.setStyleSheet("""
            QLabel {
                color: black;
                padding: 10px;
                border-radius: 1px;
                border: 1px solid black;
                font: 12pt "Segoe UI";
            }
        """)
        label.adjustSize()
        label.show()
        screen_geometry = app.primaryScreen().geometry()
        y = screen_geometry.height() - screen_geometry.height() // 3
        label.move(label.x(), y)
        QTimer.singleShot(duration, label.close)
        QTimer.singleShot(duration + 500, app.quit)
        app.exec()

if __name__ == "__main__":
    handler = mws_handler()
    handler.main()
