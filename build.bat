@echo off
cd sqlantaresia
for %%F in (*.qrc) do call pyrcc5 %%F -o "%%~nF"_rc.py
for %%F in (*.ui) do call pyuic5 --from-imports %%F -o Ui_%%~nF.py
python setup.py py2exe
