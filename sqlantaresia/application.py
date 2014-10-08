# -*- coding: utf-8 -*-

import sys

import warnings
warnings.filterwarnings("ignore", ".*sha module is deprecated.*", DeprecationWarning)
warnings.filterwarnings("ignore", ".*md5 module is deprecated.*", DeprecationWarning)


name = "SQLAntaresia"
description = "Cross platform MySQL management tools aimed at both developers and system administrators"
version = "0.5"
url = "http://github.com/mtorromeo/sqlantaresia"


def main():
    import setproctitle
    setproctitle.setproctitle("sqlantaresia")

    from PyQt5.QtWidgets import QApplication
    from .SQLAntaresia import SQLAntaresia

    app = QApplication(sys.argv)
    app.setApplicationName(name)

    window = SQLAntaresia()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
