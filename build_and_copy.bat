@echo off
rem Define Variables

set EXE_NAME=MWS_Link_Handler
set EXE_SCRIPT=mws_handler_exe.py
set INIT_SCRIPT=__init__.py
set MWS_SCRIPT=mws_handler.py
set DEST_DIR=D:\Modding\MO2\plugins\MWS Handler
set DIST_DIR=.\MWS Handler
set SEVEN_ZIP="C:\Program Files\7-Zip\7z.exe"

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
IF NOT EXIST "%DEST_DIR%" MKDIR "%DEST_DIR%""

rem copy files to destination
echo Copying the executable from "%SOURCE_EXE_PATH%" to "%DEST_DIR%"...
copy "%SOURCE_EXE_PATH%" "%DEST_DIR%"

echo Copying "%INIT_SCRIPT%" to "%DEST_DIR%"...
copy "%INIT_SCRIPT%" "%DEST_DIR%"

echo Copying "%MWS_SCRIPT%" to "%DEST_DIR%"...
copy "%MWS_SCRIPT%" "%DEST_DIR%"

echo -----------------------------------------
IF NOT EXIST "%DIST_DIR%" MKDIR "%DIST_DIR%""
echo Now copying for distribution
copy "%SOURCE_EXE_PATH%" "%DIST_DIR%"
copy "%INIT_SCRIPT%" "%DIST_DIR%"
copy "%MWS_SCRIPT%" "%DIST_DIR%"
echo -----------------------------------------
echo Zipping for distribution

%SEVEN_ZIP% a "MWS MO2 Link Handler.zip" "%DIST_DIR%" "README.txt"
echo Done