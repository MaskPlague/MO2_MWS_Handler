#Written by MaskPlauge
import mobase # type: ignore
import json

from urllib.request import urlopen

try:
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:
    from PyQt5.QtCore import QObject, pyqtSignal # type: ignore

class CheckForUpdateWorker(QObject):
    finished_signal = pyqtSignal(str, str, str)
    def __init__(self, modId, name, version_scheme):
        self.modId = modId
        self.name = name
        self.version_scheme = version_scheme
        super().__init__()

    def _get_json_from_link(self, link) -> dict:
        response = urlopen(link)
        json_data: dict = json.load(response)
        response.close()
        return json_data
    
    def _convert_time_to_version(self, time:str):
        return "d" + time.split("T")[0].replace('-', '.')

    def start(self):
        if not self.version_scheme == mobase.VersionScheme.DATE:
            mod_version_link = f"https://api.modworkshop.net/mods/{self.modId}/version"
            try:
                response = urlopen(mod_version_link)
                mod_version = response.read().decode('utf-8')
                response.close()
            except:
                mod_version = "0.0.0.0"
        else:
            mod_name_link = f"https://api.modworkshop.net/mods/{self.modId}/files/latest"
            try:
                json_data = self._get_json_from_link(mod_name_link)
                mod_time = json_data.get("updated_at", "2000-0-0T0")
            except:
                mod_time = "2000-0-0T0"
            mod_version = self._convert_time_to_version(mod_time)
        self.finished_signal.emit(self.modId, mod_version, self.name)

class UpdateCategoryWorker(QObject):
    finished_signal = pyqtSignal(str, str, str)
    def __init__(self, modId, name):
        self.modId = modId
        self.name = name
        super().__init__()

    def _get_json_from_link(self, link) -> dict:
        response = urlopen(link)
        json_data: dict = json.load(response)
        response.close()
        return json_data
    
    def start(self):
        mod_link = f"https://api.modworkshop.net/mods/{self.modId}/"
        try:
            json_data = self._get_json_from_link(mod_link)
            category_id = str(int(json_data.get("category_id", "1")))
        except:
            category_id = "1"
        self.finished_signal.emit(self.modId, category_id, self.name)