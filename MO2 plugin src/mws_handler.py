# Written by MaskPlague
import winreg
import os
import mobase # type: ignore
import json
import subprocess

from urllib.request import urlopen

from .globals import *
from .utils.data_holder import Data_Holder
from .utils.download_progress_listener import ProgressListener
from .utils.download_delegate import HybridDownloadDelegate
from .utils.event_filters import Event_Filter

try:
    from PyQt6.QtWidgets import (QMessageBox, QMainWindow, QTabWidget, QWidget, QTreeView,
                                 QApplication, QPushButton)
    from PyQt6.QtCore import Qt, QFileInfo, QTimer
except ImportError:
    from PyQt5.QtWidgets import (QMessageBox, QMainWindow, QTabWidget, QWidget, QTreeView,  # type: ignore
                                 QApplication, QPushButton)
    from PyQt5.QtCore import Qt, QFileInfo, QTimer # type: ignore

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
        self._organizer.onUserInterfaceInitialized(self._onUserInterfaceInitialized)
        self.main_window = None
        self.new_delegate = None
        self.data_holder:Data_Holder = Data_Holder()
        self.listener = ProgressListener(self.data_holder)
        self.listener.progress_received.connect(self.on_external_progress)
        self.ui_inited = False
        
        #Bat file to restart MO2
        self.bat_file_path = os.path.join(os.path.dirname(self._organizer.getPluginDataPath()), "MWS Handler/restart_mo2.bat")
        if os.path.exists(self.bat_file_path):
            os.remove(self.bat_file_path)
        
        QApplication.instance().aboutToQuit.connect(self.listener.stop)
        return True
    
    def on_external_progress(self, file_name, progress, total):
        #If total is -1 the download is complete
        if total == -1 or progress == total:
            print(f"Download completed: {file_name}")
            if file_name in self.data_holder.data:
                self.data_holder.data.pop(file_name)
            if self.data_holder.view is not None:
                self.data_holder.view.update()
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
            self.data_holder.data.update(
                {file_name: {"progress": progress, 
                             "total": total, 
                             "cancelled": self.data_holder.data.get(file_name, {"cancelled": False})["cancelled"]}})
            self.data_holder.view.update(index_status)
        
        return
    
    def categoryFileInfo(self) -> QFileInfo:
        return QFileInfo(self._organizer.basePath() + "/" + "categories.dat")
    
    def _get_json_from_link(self, link):
        response = urlopen(link)
        json_data:dict = json.load(response)
        response.close()
        return json_data
    
    def get_categories(self, game_short_name, game_name):
        categories_link = f"https://api.modworkshop.net/games/{game_short_name}/categories"
        fake_categories_data = [[1, f"1|{game_name}|0\n"]]
        categories_data = [[1, f"1|{game_name}|0\n"]]
        try:
            data = self._get_json_from_link(categories_link)
            
            for category in data["data"]:
                fake_categories_data.append([int(category["id"]), f"{category['id']}|{category['name']}|{category['id']}\n"])
                categories_data.append([int(category["id"]), f"{category['id']}|{category['name']}|{category['parent_id'] if category['parent_id'] != None else '0'}\n"])
            categories_data.sort(key=lambda c: c[0])
            fake_categories_data.sort(key=lambda c: c[0])
            categories_string = ''.join([p[1] for p in categories_data])
            fake_nexus_categories_string = ''.join([p[1] for p in fake_categories_data])
            return categories_string, fake_nexus_categories_string
        except:
            return categories_string, fake_nexus_categories_string
        
    def restart_mo2(self):
        mo2_path = QApplication.applicationFilePath()
        lines = ("@echo off",
                "::Wait unti finished",
                ":loop",
                'tasklist /fi "IMAGENAME eq ModOrganizer.exe" | find /i "ModOrganizer.exe"',
                "if %errorlevel% equ 0 (timeout /t 1 /nobreak >nul & goto loop)",
                ":: Restart MO2",
                f'start "" "{mo2_path}"')
        with open(self.bat_file_path, "w", encoding="utf-8") as f:
            f.write('\n'.join(lines))
        subprocess.Popen([self.bat_file_path], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
        QApplication.quit()

    def restart_message(self):
        button = QMessageBox.information(None, "Categories Updated from MWS", 
                                        "Category data has been updated from MWS.\nPress Ok to restart MO2 and apply changes.",
                                        QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        if button == QMessageBox.StandardButton.Ok:
            self.restart_mo2()

    def init_categories(self, wait_time=500):
        game_plugin = self._organizer.managedGame()
        if hasattr(game_plugin, "CategorySource") and game_plugin.CategorySource.lower() == "modworkshop":
            print(f"The instance's game plugin's defined CategorySource is {game_plugin.CategorySource}")
            if self.categoryFileInfo().exists() and self.categoryFileInfo().size() != 0:
                print(f"Categories.dat already contains data. Skipping retrieval from MWS.")
                return
            try:
                cat_data, nexus_cat_map = self.get_categories(game_plugin.gameShortName(), game_plugin.gameName())
                with open(os.path.join(self._organizer.basePath(), "categories.dat"), "w", encoding="utf-8") as f:
                    f.write(cat_data)
                with open(os.path.join(self._organizer.basePath(), "nexuscatmap.dat"), "w", encoding="utf-8") as f:
                    f.write(nexus_cat_map)
                QTimer.singleShot(wait_time, self.restart_message)
            except Exception as e:
                print(f"An error occurred while getting categories for {game_plugin.gameShortName()} ({game_plugin.gameName()}) from ModWorkshop API:")
                print(e)

    def _onUserInterfaceInitialized(self, main_window: QMainWindow):
        if self.ui_inited:
            return
        self.ui_inited = True

        self.init_categories()
        if self.main_window is None:
            self.main_window = main_window
        modList = main_window.findChild(QTreeView, "modList")
        tabWidget = main_window.findChild(QTabWidget, "tabWidget")
        downloadTab = tabWidget.findChild(QWidget, "downloadTab")
        self.data_holder.refresh = downloadTab.findChild(QPushButton, "btnRefreshDownloads").click
        downloadView = downloadTab.findChild(QTreeView, "downloadView")

        #Takeover the context menu for downloads
        self.event_filter = Event_Filter(
            downloadView, 
            modList,
            self.data_holder, 
            self.listener.cancel_download,
            self._organizer,
            self.init_categories
        )
        QApplication.instance().installEventFilter(self.event_filter)

        #Set game for checking if download is for correct game
        try:
            game_name = self._organizer.managedGame().gameShortName()
        except:
            game_name = "MWS_None"
        try:
            base = winreg.HKEY_CURRENT_USER
            key = winreg.OpenKey(base, fr"Software\Classes\{PROTOCOL}", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "game", 0, winreg.REG_SZ, str(game_name))
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Failed to set opened game to registry: {e}")

        #Takeover the item delegate for downloads
        current_delegate = downloadView.itemDelegate()
        if not isinstance(current_delegate, HybridDownloadDelegate):
            self.new_delegate = HybridDownloadDelegate(current_delegate, self.data_holder, downloadView)
            downloadView.setItemDelegateForColumn(STATUS_COLUMN, self.new_delegate)
            self.data_holder.view = downloadView
            self.data_holder.model = downloadView.model()

    def _mod_installed(self, mod:mobase.IModInterface):
        if mod.repository() == "ModWorkshop" and mod.nexusId() != 0:
            mod.setUrl(f"https://modworkshop.net/mod/{mod.nexusId()}")
            mod.setNexusID(0)

    def _register_protocol(self):
        download_dir = self._organizer.downloadsPath()
        plugins_dir = os.path.dirname(self._organizer.getPluginDataPath())
        self_path = os.path.join(plugins_dir, 'MWS Handler')

        # The path to the MWS link handler executable
        exe_path = os.path.normpath(os.path.join(self_path, 'MWS_Link_Handler.exe'))
        command = f'"{exe_path}" "{download_dir}" "%1"'

        # MO2 path passed for launching if the program is not open
        mo2_path = os.path.normpath(os.path.join(os.path.dirname(plugins_dir), 'ModOrganizer.exe'))
        try:
            # Use CURRENT_USER instead of CLASSES_ROOT to avoid needing admin
            base = winreg.HKEY_CURRENT_USER

            with winreg.CreateKey(base, fr"Software\Classes\{PROTOCOL}") as key:
                winreg.SetValueEx(key, None, 0, winreg.REG_SZ, fr"URL:{PROTOCOL.upper()} Protocol")
                winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
                winreg.SetValueEx(key, 'mo_path', 0, winreg.REG_SZ, fr"{mo2_path}")
                winreg.SetValueEx(key, 'port', 0, winreg.REG_SZ, "-1")

                # Set the command for shell\open\command
                with winreg.CreateKey(key, r"shell\open\command") as subkey:
                    winreg.SetValueEx(subkey, None, 0, winreg.REG_SZ, command)

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