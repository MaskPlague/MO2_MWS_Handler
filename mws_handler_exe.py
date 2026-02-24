import sys
import os
import winreg
from threading import Thread
import json
import socket
import time
import subprocess

import tkinter as tk
from tkinter import messagebox

from urllib.request import urlretrieve
from urllib.request import urlopen
from urllib.parse import unquote

#Fix MO2 grabbing vcruntime dlls from temp _MEI folder
if sys.platform == "win32":
    import ctypes
    ctypes.windll.kernel32.SetDllDirectoryA(None)

#Compile command: pyinstaller mws_handler_exe.py --onefile -n MWS_Link_Handler --noconsole
PROTOCOL = "mws-mo2"
DEBUG = False

def debug_print(string):
    if DEBUG:
        print(string)

class mws_handler():
    def __init__(self):   
        self.mod_name = "Unknown"
        self.file_version = "0.0.0.0"
        self.mod_version = "0.0.0.0"
        self.mod_last_updated = "2000-0-0T0"
        self.file_last_updated = "2000-0-0T0"
        self.cancelled = False
        self.sock = None
        self.downloading = True
        self.e = None

    def main(self):
        #sys.argv should be [exe, download location, mws url protocol link]
        if len(sys.argv) > 2:
            download_location = sys.argv[1]
            #sys.argv[2] is link and it should be mws-mo2://install/game_id/mod_id/file_id
            game_id, mod_id, file_id = self.get_ids_from_link(sys.argv[2])
            download_link = f"https://api.modworkshop.net/files/{file_id}/download"
            error = None
            try:
                last_game = self._get_from_registry('game')
            except Exception as e:
                last_game = "MWS_None"
                error = e

            #If the game instance does not match do not download
            if last_game != "MWS_None" and last_game != game_id:
                self._show_message(f'Download is for "{game_id}" but, the last opened instance is for "{last_game}".\nDownload cancelled.', 5000)
                return
            elif last_game == "MWS_None":
                self._show_message('An error was encountered while getting the last opened MO2 instance game name.\n'+
                                  'Ensure the MWS MO2 plugin is installed and then restart MO2.\n'+
                                 f'Error: {error}\n'+
                                  'Download Cancelled.', 5000)
                return

            #Get filename and determine if the api is working                
            try:
                response = urlopen(download_link)
                filename = unquote(response.headers.get_filename())
                response.close()
            except:
                self._show_message(f'Cannot connect to https://api.modworkshop.net/.\nDownload cancelled.', 5000)
                return

            #Get the latest version of the mod and file
            file_version_thread = Thread(target=self._get_file_version_and_date_from_api, args=(file_id,), daemon=True)
            file_version_thread.start()
            
            mod_version_thread = Thread(target=self._get_mod_version_from_api, args=(mod_id,), daemon=True)
            mod_version_thread.start()

            debug_print("Download Started")
            self._show_message('Download Started', 1500)

            file_version_thread.join()
            mod_version_thread.join()

            #if either the mod or file has no version then use the last update time instead for both
            if self.mod_version.strip() == "" or self.file_version.strip() == "":
                self._get_latest_file_date_from_api(mod_id)
                self.mod_version = self._convert_time_to_version(self.mod_last_updated)
                self.file_version = self._convert_time_to_version(self.file_last_updated)

            #insert the version in the file name for checking if the current file version has already been downloaded
            name, ext = os.path.splitext(filename)
            filename = name + "-" + self.file_version + ext

            #Get an available file name
            available_name = self._get_available_name(download_location, filename)

            download_path = os.path.join(download_location, available_name)

            #Open MO2 if it isn't currently running
            open_mo2_thread = Thread(target=self.open_mo2_if_not_running, daemon=True)
            open_mo2_thread.start()

            #If the file has already been downloaded
            if available_name != filename:
                cont = self.ask_to_continue(filename)
                if not cont:
                    if os.path.exists(download_path):
                        os.remove(download_path)
                    return
                
            download_thread = Thread(target=self.download_file, args=(download_link, download_path, available_name), daemon=True)
            download_thread.start()

            cancel_thread = Thread(target=self.listen_for_cancel, daemon=True)
            cancel_thread.start()

            name_thread = Thread(target=self._get_mod_name_from_api, args=(mod_id,), daemon=True)
            name_thread.start()

            name_thread.join()

            download_metadata_path = os.path.join(download_location, available_name + '.meta')
            download_thread.join()
            if self.cancelled:
                self._show_message(f"Download for {filename} cancelled.\n{self.e}", 3000)
            elif self.e is not None:
                self._show_message(f"Failed to download file \"{filename}\" from: {download_link}\nError: {self.e}", 5000)
            else:
                self.save_download_metadata(download_metadata_path, game_id, mod_id, file_id, filename)
            open_mo2_thread.join()
            sys.exit(0)

    def get_ids_from_link(self, link):
        split = link.split('/')
        return split[-3], split[-2], split[-1] #game_id, mod_id, file_id


    def save_download_metadata(self, path, game_id, mod_id, file_id, filename):
        with open(path, 'w', encoding='utf-8') as f:
            f.write("[General]\n"+
                    "removed=false\n"+
                    f"gameName={game_id}\n"+
                    f"modID={mod_id}\n"+
                    f"fileID={file_id}\n"+
                    f"url=https://modworkshop.net/mod/{mod_id}\n"+                                  
                    f"hasCustomUrl=true\n"+                                                         #Replaced "Open On Nexus" with MWS via MO2 plugin
                    f"name={os.path.splitext(filename)[0]}\n"+
                    "description=\n"+                                                               #Maybe in the future
                    f"modName={self.mod_name}\n"+
                    f"version={self.file_version}\n"+
                    f"newestVersion={self.mod_version}\n"+
                    f"fileTime=@DateTime({r'\0\0\0\x10\0\x80\0\0\0\0\0\0\0\xff\xff\xff\xff\0'})\n"+ #Couldn't find an example where this is used
                    "fileCategory=0\n"+
                    "category=0\n"+
                    "repository=ModWorkshop\n"+
                    f"userData=@Variant({r'\0\0\0\b\0\0\0\0'})\n"+
                    "installed=false\n"+
                    "uninstalled=false\n"+
                    "paused=false")
            f.close()

    def listen_for_cancel(self):
        try:
            while self.downloading:
                if self.connected and not self.cancelled:
                    try:
                        data = self.sock.recv(1024)
                    except:
                        continue
                    if not data:
                        break
                    try:
                        msg = json.loads(data.decode('utf-8'))
                        if msg.get("action") == "cancel":
                            self.cancelled = True
                            break
                    except:
                        pass
                else:
                    time.sleep(0.5)
        except:
            pass

    def _get_from_registry(self, reg_key:str):
        base = winreg.HKEY_CURRENT_USER
        key = winreg.OpenKey(base, fr"Software\Classes\{PROTOCOL}")
        val = winreg.QueryValueEx(key, reg_key)[0]
        winreg.CloseKey(key)
        return val

    def download_file(self, download_link, download_path, filename):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        connecting = False
        socket.setdefaulttimeout(15)
        def try_connect():
            nonlocal connecting
            try:
                port = int(self._get_from_registry('port'))
                if port != -1:
                    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.sock.connect(('127.0.0.1', port))
                    self.connected = True
                    debug_print(f"conneted on port: {port}")
            except:
                self.connected = False
            finally:
                connecting = False

        try_connect()

        def send_msg(filename, cur, max):
            msg = {
                "file": filename,
                "cur": cur,
                "max": max
            }
            self.sock.sendall((json.dumps(msg) + "\n").encode('utf-8'))

        def progress_hook(block_num, block_size, total_size):
            nonlocal connecting
            if self.cancelled:
                debug_print("progress_hook, user cancelled download")
                raise InterruptedError("User Cancelled Download")
            if self.connected:
                try:
                    current_downloaded = block_num * block_size
                    send_msg(filename, current_downloaded, total_size)
                except:
                    debug_print("closing socket")
                    self.connected = False
                    try:
                        self.sock.close()
                    except:
                        pass
            elif not connecting and not self.cancelled and self.downloading:
                connecting = True
                debug_print("Trying to connect to MO2 plugin")
                Thread(target=try_connect, daemon=True).start()

        def remove(download_path, filename):
            try:
                if not self.connected:
                    try_connect()
                if self.connected:
                    send_msg(filename, -1, -1)
            finally:
                if os.path.exists(download_path):
                    try:
                        os.remove(download_path)
                    except:
                        pass
        try:
            try:
                if DEBUG:
                    start = time.time()
                urlretrieve(download_link, download_path, reporthook=progress_hook)
                if DEBUG:
                    end = time.time()
                    debug_print(f"Time taken {end-start} seconds")
            except InterruptedError as e:
                debug_print(f"Canceled: {e}")
                self.e = e
                remove(download_path, filename)
            except TimeoutError as e:
                debug_print(f"Canceled: {e}")
                self.e = "Download has timed out."
                remove(download_path, filename)
            except Exception as e:
                debug_print(f"Exception: {e}")
                self.e = e
                remove(download_path, filename)

            debug_print(f"send download complete message: {self.connected}")
            if not self.connected:
                try_connect()
            if self.connected:
                try:
                    send_msg(filename, -1, -1)
                    debug_print("Sent completion message")
                except:
                    pass
        finally:
            debug_print("finishing up download")
            self.downloading = False
            try:
                debug_print("closing socket")
                self.sock.close()
            except:
                pass

    def _convert_time_to_version(self, time:str):
        return "d" + time.split("T")[0].replace('-', '.')
    
    def _get_json_from_link(self, link):
        response = urlopen(link)
        json_data:dict = json.load(response)
        response.close()
        return json_data

    def _get_mod_name_from_api(self, mod_id):
        mod_name_link = f"https://api.modworkshop.net/mods/{mod_id}"
        try:
            json_data = self._get_json_from_link(mod_name_link)
            self.mod_name = json_data.get("name", mod_id)
        except:
            self.mod_name = mod_id
    
    def _get_latest_file_date_from_api(self, mod_id):
        mod_name_link = f"https://api.modworkshop.net/mods/{mod_id}/files/latest"
        try:
            json_data = self._get_json_from_link(mod_name_link)
            self.mod_last_updated = json_data.get("updated_at", "2000-0-0T0")
        except:
            self.mod_last_updated = "2000-0-0T0"
            pass

    def _get_file_version_and_date_from_api(self, file_id):
        file_version_link = f"https://api.modworkshop.net/files/{file_id}"
        try:
            json_data = self._get_json_from_link(file_version_link)
            self.file_version = json_data.get("version", "")
            self.file_last_updated = json_data.get("updated_at", "2000-0-0T0")
        except:
            self.file_version = ""
            self.file_last_updated = "2000-0-0T0"

    def _get_mod_version_from_api(self, mod_id):
        mod_version_link = f"https://api.modworkshop.net/mods/{mod_id}/version"
        try:
            response = urlopen(mod_version_link)
            self.mod_version = response.read().decode('utf-8')
            response.close()
        except:
            self.mod_version = ""

    def _get_available_name(self, download_location, name, number = 0):
        if number == 0:
            new_name = name
        else:
            split = os.path.splitext(name)
            new_name = str(number) + '_' + split[0] + split[1]
        
        download_path = os.path.join(download_location, new_name)
        
        #Done this way to reserve the file name before download starts
        try:
            with open(download_path, 'x') as f:
                pass
            return new_name
        except:
            return self._get_available_name(download_location, name, number+1)
        
    def is_mo2_running(self):
        output = subprocess.check_output('tasklist /fi "imagename eq ModOrganizer.exe"', shell=True)
        return b"ModOrganizer.exe" in output
    
    def open_mo2_if_not_running(self):
        if not self.is_mo2_running():
            try:
                mo2_path = self._get_from_registry('mo_path')
                
                if os.path.exists(mo2_path):
                    os.startfile(mo2_path)
                    return
            except:
                pass

    def _show_message(self, msg, duration=2000):
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes('-topmost', True)

        label = tk.Label(
            root, 
            text=msg, 
            font=("Segoe UI", 12),
            fg="black",
            bg="#f0f0f0",
            padx=10,
            pady=10,      
            relief="solid",
            borderwidth=1
        )
        label.pack()
        root.update_idletasks() 
        
        width = root.winfo_width()
        height = root.winfo_height()
        screen_height = root.winfo_screenheight()
        sceeen_width = root.winfo_screenwidth()

        x_pos = (sceeen_width // 2) - (width // 2)
        y_pos = (screen_height - (screen_height // 3)) - (height // 2)
        
        root.geometry(f'{width}x{height}+{x_pos}+{y_pos}')

        root.after(duration, root.destroy)
        root.mainloop()
    
    def ask_to_continue(self, filename):
        result = False
        def ask():
            nonlocal result
            result = messagebox.askyesno("Download again?",
                                        f"A file with the same name \"{filename}\" has already "+
                                        "been downloaded. Do you want to download it again? The "+
                                        "new file will recieve a different name.")
            root.destroy()
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes('-topmost', True)
        root.geometry(f'0x0+-10+-10')
        root.after(50, ask)
        root.mainloop()
        return result

if __name__ == "__main__":
    handler = mws_handler()
    handler.main()
