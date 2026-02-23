Installation:
	- Copy the MWS Handler and basic_games folder to your MO2/Plugins/ folder.


Change log:
- 0.0.2:
    - mws-mo2://install/:game_id/:mod_id/:file_id

    - Changed protocol from MWS to MWS-MO2.

    - Uses the elements of the MWS-MO2 link to populate the download metadata file. 

- 0.0.3:
    - Gets the mod name (modName=), file version (version=), and mod version (newestVersion=) from the MWS API and puts them
    - into the metadata file.

- 0.0.4:
    - Support for BLT and SuperBLT Libraries

    - If the file or mod version cannot be gotten then their last update dates are used instead.
    - Add callback on mod install in MO2, if the file repository is ModWorkshop's a custom url is added in the meta.ini for the mod's page.
    - MO2 v2.4 support for MWS Handler via try catch importing PyQt5

- 0.1.0:
    - Added download progress to MO2 downloads tab

- 0.1.1:
    - Reject a download when it is for a different game then the last opened game instance.

- 0.1.2:
    - Added cancel download button to context menu of MO2 downloads
    - Fix "Failed to delete temp folder" issue
    - Fix race condition that would occur if you spammed the download button.

- 0.1.3:
    - Set nexus mod id to 0 when a mod from MWS is installed to disable the "Visit on Nexus" option in the modlist context menu

- 0.1.5:
    - Convert to tkinter from PyQt6. Reduces exe size from 36.3MB to 11.9MB
    - Fix slow downloads when MO2 is closed
    - Change duplicate download logic to replicate MO2's. We now ask the user if they want to redownload the file.
