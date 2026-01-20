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
