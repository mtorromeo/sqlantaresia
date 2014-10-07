#!/bin/sh
PYRCC=pyrcc5
PYUIC=pyuic5
cd sqlantaresia
for qrc in *.qrc; do
	$PYRCC "$qrc" -o "$(basename "$qrc" ".qrc")_rc.py"
done
for ui in *.ui; do
	$PYUIC "$ui" -o "Ui_$(basename "$ui" ".ui").py"
done
