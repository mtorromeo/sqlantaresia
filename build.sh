#!/bin/sh
PYRCC=pyrcc4
PYUIC=pyuic4
which -s pyrcc4-2.6 > /dev/null 2>&1 && PYRCC=pyrcc4-2.6
which -s pyuic4-2.6 > /dev/null 2>&1 && PYUIC=pyuic4-2.6
cd sqlantaresia
for qrc in *.qrc; do
	$PYRCC "$qrc" -o "$(basename "$qrc" ".qrc")_rc.py"
done
for ui in *.ui; do
	$PYUIC "$ui" -o "Ui_$(basename "$ui" ".ui").py"
done
