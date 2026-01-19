#Written by MaskPlauge
import winreg
import os
import mobase

from PyQt6.QtWidgets import QMessageBox

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
        return True

    def _register_protocol(self):
        protocol = "mws-mo2"
        download_dir = self._organizer.downloadsPath()
        self_path = os.path.join(os.path.split(self._organizer.getPluginDataPath())[0], 'MWS Handler')

        # Code for testing via python
        #exe_path = os.path.abspath(os.path.join(self_path, 'mws_handler_exe.py'))
        #profile_name = os.getlogin()
        #temp_python_exe = os.path.abspath(fr"C:\Users\{profile_name}\AppData\Local\Programs\Python\Python313\python.exe")
        #command = f'"{temp_python_exe}" "{exe_path}" "{download_dir}" "%1"'

        # The path to the MWS link handler executable
        exe_path = exe_path = os.path.abspath(os.path.join(self_path, 'MWS_Link_Handler.exe'))
        command = f'"{exe_path}" "{download_dir}" "%1"'

        # MO2 path passed for launching if the program is not open
        mo2_path = os.path.join(*os.path.normpath(self_path).split(os.sep)[:3], 'ModOrganizer.exe')
        try:
            # Use CURRENT_USER instead of CLASSES_ROOT to avoid needing admin
            base = winreg.HKEY_CURRENT_USER
            key = winreg.CreateKey(base, fr"Software\Classes\{protocol}")
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ, "URL:MWS-MO2 Protocol")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            winreg.SetValueEx(key, 'mo_path', 0, winreg.REG_SZ, fr"{mo2_path}")

            # Set the command for shell\open\command
            subkey = winreg.CreateKey(key, r"shell\open\command")
            winreg.SetValueEx(subkey, None, 0, winreg.REG_SZ, command)
            winreg.CloseKey(key)

            print(f"Registered protocol '{protocol}' with handler: {command}")
            self._organizer.setPluginSetting(self.name(), "MWS-MO2 Protocol Registered", True)

        except Exception as e:
            print(f"Failed to register protocol: {e}")
            self._organizer.setPluginSetting(self.name(), "MWS-MO2 Protocol Registered", False)
            QMessageBox.warning(None, "MWS-MO2 Protocol Register Failed", "Failed to regester protocol to the registry for MWS-MO2 links (ModWorkshop.net)")

    def settings(self):
        return [
            mobase.PluginSetting("MWS-MO2 Protocol Registered", "Indicates if MWS-MO2 links are handled, changing this does nothing.", False)
            ]
    
    def description(self):
        return "Registers the MWS-MO2 protocol to handle downloads."
    