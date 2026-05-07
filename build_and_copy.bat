@echo off

rem Define Variables
set EXE_NAME=MWS_Link_Handler
set EXE_SCRIPT=mws_handler_exe.py
set M02_PLUGIN_SRC=.\MO2 plugin src
set DIST_DIR=.\MWS plugin dist

rem Replace these with your own directories
set DEST_MO2_PLUGIN_DIR=D:\Modding\MO2\plugins\MWS Handler
set SEVEN_ZIP="C:\Program Files\7-Zip\7z.exe"

rem Build EXE via PyInstaller
echo Starting PyInstaller build for %EXE_SCRIPT%...
pyinstaller %EXE_SCRIPT% --onefile -n %EXE_NAME% --noconsole

rem Check if PyInstaller was successful

IF %ERRORLEVEL% NEQ 0 (
    echo PyInstaller build failed!
    pause
    EXIT /B 1
)
echo -----------------------------------------

set SOURCE_EXE_PATH=.\dist\%EXE_NAME%.exe

rem create dest if it doesn't exist
IF NOT EXIST "%DEST_MO2_PLUGIN_DIR%" MKDIR "%DEST_MO2_PLUGIN_DIR%""

rem copy files to destination
echo Copying the executable from "%SOURCE_EXE_PATH%" to "%DEST_MO2_PLUGIN_DIR%"...
copy "%SOURCE_EXE_PATH%" "%DEST_MO2_PLUGIN_DIR%"

echo Copying "%M02_PLUGIN_SRC%" to "%DEST_MO2_PLUGIN_DIR%"...
robocopy "%M02_PLUGIN_SRC%" "%DEST_MO2_PLUGIN_DIR%" /E

echo -----------------------------------------
IF NOT EXIST "%DIST_DIR%" MKDIR "%DIST_DIR%""
echo Now copying for distribution
copy "%SOURCE_EXE_PATH%" "%DIST_DIR%"
robocopy "%M02_PLUGIN_SRC%" "%DIST_DIR%" /E

echo -----------------------------------------
echo Zipping for distribution

%SEVEN_ZIP% a "MWS Handler.zip" "%DIST_DIR%" "changelog.txt"

echo Done