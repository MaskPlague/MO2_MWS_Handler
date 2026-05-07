#Written by MaskPlauge
import os
import mobase # type: ignore
import configparser
import webbrowser

from .data_holder import Data_Holder
from ..globals import *
from .workers import *

try:
    from PyQt6.QtWidgets import QTreeView, QMenu
    from PyQt6.QtCore import Qt, QObject, QEvent, QThread, QSettings, QTimer
    from PyQt6.QtGui import QAction
except ImportError:
    from PyQt5.QtWidgets import QTreeView, QMenu # type: ignore
    from PyQt5.QtCore import Qt, QObject, QEvent, QThread, QSettings, QTimer # type: ignore
    from PyQt5.QtGui import QAction # type: ignore

class Event_Filter(QObject):
    def __init__(self, download_view, modList_view, data_holder, cancel_callback, organizer: mobase.IOrganizer, init_categories):
        super().__init__()
        self.download_view: QTreeView = download_view
        self.modList_view: QTreeView = modList_view
        self.data_holder: Data_Holder = data_holder
        self.cancel_callback = cancel_callback
        self.modList: mobase.IModList = organizer.modList()
        self.download_path = organizer.downloadsPath()
        self._organizer = organizer
        self.init_categories = init_categories
        self.init_vars()

    def _refresh(self):
        self._organizer.refresh()

    def _init_categories(self):
        self.init_categories()

    def init_vars(self):
        self.visit_mws_action = None

        self.check_for_update_action = None
        self.update_missing_category_action = None

        # dicts to hold pointers to worker objects and threads to keep them alive until finished
        self.update_check_workers = {}
        self.update_check_threads = {}

        self.category_workers = {}
        self.category_threads = {}

        #List of mod ids that have recently been checked for an update within API_WAIT_TIME_MSEC to prevent API spam
        self.recently_checked_for_update = []

        self.recently_got_categories = False

        self.menu_obtained = False
        self.listOptions_menu: QMenu = None
        self.next = False
        self.menu_check_all_for_update_action = QAction("Check for updates (MWS)")
        self.menu_check_all_for_update_action.triggered.connect(self.check_all_for_update)
        self.menu_update_mod_categories_action = QAction("Get Missing Categories (MWS)")
        self.menu_update_mod_categories_action.triggered.connect(self.update_all_mod_categories)
        self.menu_clear_and_get_categories_action = QAction("Reset and Get Category Data (MWS)")
        self.menu_clear_and_get_categories_action.triggered.connect(self.clear_and_get_categories)
        self.separator: QAction = None

    def eventFilter(self, obj: QObject, event: QEvent):
        if event.type() == QEvent.Type.Show and isinstance(obj, QMenu):
            if obj.parent() == self.download_view:      # if context menu is for a download
                self.change_context_menu_download(obj)
            elif obj.parent() == self.modList_view and len(obj.actions()) >= 7:     # if context menu for a mod in the mod list
                self.change_context_menu_mod_list(obj)

        if not self.menu_obtained:  # if we haven't grabbed the listOptions menu
            if event.type() == QEvent.Type.MouseButtonPress and obj.objectName() == "listOptionsBtn":
                self.next = True    # next menu event will be for the listOptions menu
            elif self.next and isinstance(obj, QMenu):  # get the list options menu
                self.next = False
                self.menu_obtained = True
                self.listOptions_menu = obj
        elif event.type() == QEvent.Type.Show and obj == self.listOptions_menu: #on list options menu display add the MWS actions, if statements prevent accidental duplication of actions
            if self.separator == None:
                self.separator = self.listOptions_menu.addSeparator()
                def set_none():
                    self.separator = None
                self.separator.destroyed.connect(set_none)
            if not self.menu_check_all_for_update_action in self.listOptions_menu.actions(): 
                self.listOptions_menu.addAction(self.menu_check_all_for_update_action)
            if not self.menu_update_mod_categories_action in self.listOptions_menu.actions(): 
                self.listOptions_menu.addAction(self.menu_update_mod_categories_action)
            if not self.menu_clear_and_get_categories_action in self.listOptions_menu.actions(): 
                self.listOptions_menu.addAction(self.menu_clear_and_get_categories_action)
        
        return False

    def change_context_menu_download(self, menu: QMenu):
        selection_model = self.download_view.selectionModel()
        if not selection_model.hasSelection():
            return
        index = selection_model.currentIndex()
        file_name = index.sibling(index.row(), FILENAME_COLUMN).data(Qt.ItemDataRole.DisplayRole)

        if file_name in self.data_holder.data:
            for i, action in enumerate(menu.actions()):
                if i not in (3,4,5):
                    menu.removeAction(action)
            action = menu.addAction("Cancel Download (MWS)")
            def cancel_callback(): 
                self.cancel_callback(file_name)
            action.triggered.connect(cancel_callback)
        else:
            meta_file = os.path.join(self.download_path,file_name) +'.meta'
            try:
                ini = configparser.ConfigParser()
                ini.read(meta_file, encoding="utf-8")
                repo = ini.get("General", "repository")
                if repo == "ModWorkshop":
                    url = ini.get("General", "url")
                    menu.removeAction(menu.actions()[1])
                    self.visit_mws_action = QAction("Visit on ModWorkshop")
                    def open_mws_link(): 
                        webbrowser.open(url)       
                    self.visit_mws_action.triggered.connect(open_mws_link)
                    menu.insertAction(menu.actions()[1], self.visit_mws_action)
            except Exception as e:
                pass
    
    def change_context_menu_mod_list(self, menu:QMenu):
        selection_model = self.modList_view.selectionModel()
        if not selection_model.hasSelection():
            return
        index = selection_model.currentIndex()
        file_name = index.sibling(index.row(), FILENAME_COLUMN).data(Qt.ItemDataRole.DisplayRole)
        mod_handle = self.modList.getMod(file_name)
        if mod_handle is None:
            return
        if mod_handle.repository() == "ModWorkshop":
            self.check_for_update_action = QAction("Check for Update (MWS)")
            self.check_for_update_action.triggered.connect(lambda checked, mh=mod_handle: self.check_for_update(mh))
            menu.insertAction(menu.actions()[5], self.check_for_update_action)
            if not mod_handle.categories():
                self.update_missing_category_action = QAction("Get Missing Category (MWS)")
                self.update_missing_category_action.triggered.connect(lambda checked, mh=mod_handle: self.update_mod_category(mod_handle))
                menu.insertAction(menu.actions()[6], self.update_missing_category_action)
    
    def check_for_update(self, mod_handle: mobase.IModInterface):
        if mod_handle.url() == "":
            print(f"[{mod_handle.name()}] has no custom url to get the mod id from. Skipping.")
            return
        modId = mod_handle.url().split('/')[-1]
        if modId in self.update_check_workers:
            print(f"[{mod_handle.name()}] is already being checked for an update. Skipping.")
            return
        if modId in self.recently_checked_for_update:
            print(f"[{mod_handle.name()}] was recently checked for an update within the last {API_WAIT_TIME_MSEC/1000} seconds. Skipping to prevent API spam.")
            return
        self.recently_checked_for_update.append(modId)
        def remove_from_recent_update_list(): 
            if modId in self.recently_checked_for_update: 
                self.recently_checked_for_update.remove(modId)
        QTimer.singleShot(API_WAIT_TIME_MSEC, remove_from_recent_update_list)
        old_version = mod_handle.newestVersion()
        worker = CheckForUpdateWorker(modId, mod_handle.name(), old_version.scheme())
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.start)
        worker.finished_signal.connect(thread.quit)
        worker.finished_signal.connect(self.update_worker_finished)
        worker.finished_signal.connect(worker.deleteLater)
        self.update_check_workers[modId] = worker
        self.update_check_threads[modId] = thread
        thread.start()

    def check_all_for_update(self):
        for mod_name in self.modList.allMods():
            mod_handle = self.modList.getMod(mod_name)
            if mod_handle is not None and mod_handle.repository() == "ModWorkshop":
                self.check_for_update(mod_handle)

    def update_worker_finished(self, modId, version, mod_name):
        if modId in self.update_check_workers:
            self.update_check_workers.pop(modId)
        if modId in self.update_check_threads:
            thread = self.update_check_threads.pop(modId)
            thread.wait()
        mod_handle = self.modList.getMod(mod_name)
        if mod_handle is None:
            return
        mo_version = mobase.VersionInfo(version)
        mod_handle.setNewestVersion(mo_version)

    def update_mod_category(self, mod_handle: mobase.IModInterface):
        if mod_handle.url() == "":
            print(f"[{mod_handle.name()}] has no custom url to get the mod id from. Skipping.")
            return
        modId = mod_handle.url().split('/')[-1]
        if modId in self.category_workers:
            print(f"[{mod_handle.name()}] is already having its category added. Skipping.")
            return
        if mod_handle.categories():
            if mod_handle.primaryCategory() != 1 or len(mod_handle.categories()) > 1:
                print(f"[{mod_handle.name()}] already has category data (id not -1 or 1). Skipping.")
                return
        worker = UpdateCategoryWorker(modId, mod_handle.name())
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.start)
        worker.finished_signal.connect(thread.quit)
        worker.finished_signal.connect(self.category_worker_finished)
        worker.finished_signal.connect(worker.deleteLater)
        self.category_workers[modId] = worker
        self.category_threads[modId] = thread
        thread.start()

    def category_worker_finished(self, modId, category_id, mod_name):
        if modId in self.category_workers:
            self.category_workers.pop(modId)
        if modId in self.category_threads:
            thread = self.category_threads.pop(modId)
            thread.wait()
        mod_handle = self.modList.getMod(mod_name)
        if mod_handle is None:
            return
        meta = QSettings(os.path.join(mod_handle.absolutePath(), 'meta.ini'), QSettings.Format.IniFormat, None)
        meta.setValue("category", category_id+",")
        if not self.category_workers:
            self._refresh()

    def update_all_mod_categories(self):
        for mod_name in self.modList.allMods():
            mod_handle = self.modList.getMod(mod_name)
            if mod_handle is not None and mod_handle.repository() == "ModWorkshop":
                self.update_mod_category(mod_handle)

    def clear_and_get_categories(self):
        if self.recently_got_categories:
            return
        self.recently_got_categories = True
        def set_false():
            self.recently_got_categories = False
        QTimer.singleShot(API_WAIT_TIME_MSEC, set_false)
        cat_dat_path = os.path.join(self._organizer.basePath(), "categories.dat")
        nexus_cat_map_dat_path = os.path.join(self._organizer.basePath(), "nexuscatmap.dat")
        if os.path.exists(cat_dat_path):
            os.remove(cat_dat_path)
        if os.path.exists(nexus_cat_map_dat_path):
            os.remove(nexus_cat_map_dat_path)
        self._init_categories()