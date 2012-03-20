# -*- coding: utf-8 -*-

import sip, os, sys
sip.setapi("QString", 2)
sip.setapi("QVariant", 2)

import warnings
warnings.filterwarnings("ignore", ".*sha module is deprecated.*", DeprecationWarning)
warnings.filterwarnings("ignore", ".*md5 module is deprecated.*", DeprecationWarning)


name = "SQLAntaresia"
description = "Cross platform MySQL management tools aimed at both developers and system administrators"
version = "0.3"
url = "http://github.com/mtorromeo/sqlantaresia"


def main():
    import setproctitle
    setproctitle.setproctitle("sqlantaresia")

    from PyQt4.QtGui import QApplication
    from SQLAntaresia import SQLAntaresia

    app = QApplication(sys.argv)
    app.setApplicationName(name)

    window = SQLAntaresia()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
