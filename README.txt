Installation:
Copy the MWS Handler folder to your MO2/Plugins/ folder.

0.0.2:
mws-mo2://install/:game_id/:mod_id/:file_id

Changed protocol from MWS to MWS-MO2.

Uses the elements of the MWS-MO2 link to populate the download metadata file. 

0.0.3:
Gets the mod name (modName=), file version (version=), and mod version (lastestVersion=) from the MWS api and puts them
into the metadata file.