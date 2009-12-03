@echo off
cd src
for %%F in (*.qrc) do call pyrcc4 %%F -o "%%~nF"_rc.py
for %%F in (*.ui) do call pyuic4 %%F -o Ui_%%~nF.py
python setup.py py2exe