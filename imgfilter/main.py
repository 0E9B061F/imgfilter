import sys
import os
import glob
import argparse
import math
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QLineEdit, QSizePolicy, QLayout
from PySide6.QtCore import Qt, QMargins, QPoint, QRect, QSize, QTimer


DELAY = 250
LIMIT = 50
MINTH = 50
THUMB = 300
GAP = 3
INSET = 10

class Contents(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.selected = None

    def select(self, tile):
        if self.selected:
            self.selected.deselect()
        self.selected = tile
        self.selected.select()


class TiledLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setSpacing(GAP)

        if parent is not None:
            self.setContentsMargins(QMargins(0, 0, 0, 0))

        self._item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]

        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        gap = self.spacing()
        th = self.thumb(width)
        xc = self._calcXC(width, th, gap)
        c = len(self._item_list)
        yc = math.ceil(c / xc)
        return (yc * th) + ((yc - 1) * gap)

    def setGeometry(self, rect):
        super(TiledLayout, self).setGeometry(rect)
        self._do_layout(rect)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())

        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size

    def thumb(self, width):
        gap = self.spacing()
        return min((width - gap) / 2, THUMB)

    def _calcXC(self, width, th, gap):
        used = th
        n = 1
        if used >= width:
            return n
        next = used + gap + th
        while next <= width:
            used = next
            n += 1
            next = used + gap + th
        return n

    def _do_layout(self, rect):
        w = rect.width()
        th = self.thumb(w)
        gap = self.spacing()
        xc = self._calcXC(w, th, gap)
        used = (xc * th) + ((xc - 1) * gap)
        waste = w - used
        margin = waste / 2

        x = rect.x() + margin
        y = rect.y()

        tx = 0
        ty = 0

        for item in self._item_list:
            item.setGeometry(QRect(x, y, th, th))
            tx += 1
            if tx >= xc:
                tx = 0
                ty += 1
                x = rect.x() + margin
                y = y + gap + th
            else:
                x = x + gap + th

class Label(QLabel):

    def __init__(self, parent):
        super(Label, self).__init__(parent)
        self.pixmap_width: int = 1
        self.pixmapHeight: int = 1

    def setPixmap(self, pm: QPixmap) -> None:
        self.pixmap_width = pm.width()
        self.pixmapHeight = pm.height()

        self.updateMargins()
        super(Label, self).setPixmap(pm)

    def resizeEvent(self, a0) -> None:
        self.updateMargins()
        super(Label, self).resizeEvent(a0)

    def updateMargins(self):
        if self.pixmap() is None:
            return
        pixmapWidth = self.pixmap().width()
        pixmapHeight = self.pixmap().height()
        if pixmapWidth <= 0 or pixmapHeight <= 0:
            return
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return

        if w * pixmapHeight > h * pixmapWidth:
            m = int((w - (pixmapWidth * h / pixmapHeight)) / 2)
            self.setContentsMargins(m, 0, m, 0)
        else:
            m = int((h - (pixmapHeight * w / pixmapWidth)) / 2)
            self.setContentsMargins(0, m, 0, m)

class Tile(Label):
    def __init__(self, parent, args, path, original):
        super().__init__(parent)
        self.contents = parent
        self.args = args
        self.path = path
        self.original = original

    def mousePressEvent(self, event):
        print(self.path, end='')
        quit(0)

    def enterEvent(self, event):
        self.contents.select(self)

    def select(self):
        self.setStyleSheet(f"background-color: {self.args.fg}")

    def deselect(self):
        self.setStyleSheet(f"background-color: {self.args.matte}")

    def scaleImg(self):
        self.setPixmap(self.original.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

class MainWindow(QMainWindow):
    def __init__(self, args):
        super().__init__()

        #self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.BypassWindowManagerHint)

        self.args = args

        self.path = args.path
        self.query = args.query

        self.setLayoutDirection(Qt.LeftToRight)

        self.setContentsMargins(0,0,0,0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        # Main widget and its layout
        self.central = QWidget(self)
        self.central.setContentsMargins(0, 0, 0, 0)
        self.centralLayout = QVBoxLayout(self.central)
        self.centralLayout.setSpacing(0)
        self.centralLayout.setContentsMargins(0,0,0,0)

        # Create header widget
        self.head = QWidget(self)
        self.headLayout = QHBoxLayout(self.head)
        self.headLayout.setSpacing(0)
        self.headLayout.setContentsMargins(0, 0, 0, 0)

        # Create and add prompt to header
        if len(args.prompt) > 0:
            self.prompt = QLabel(self.head)
            self.prompt.setText(args.prompt)
            self.prompt.setStyleSheet(
                f"background-color: {self.args.fg};"
                f"color: {self.args.hilite};"
                f"font-size: 16px;"
                f"font-weight: bold;"
                f"font-family: {args.fn};"
                "padding-left: 5px;"
            )
            self.headLayout.addWidget(self.prompt)

        # Create and add line input to header
        self.lineEdit = QLineEdit(self.central)
        self.lineEdit.insert(self.query)
        self.lineEdit.textChanged[str].connect(self.edit)
        self.headLayout.addWidget(self.lineEdit)

        # Add head to central layout
        self.centralLayout.addWidget(self.head)

        self.timer = QTimer()
        self.timer.timeout.connect(self.populate)

        self.scrollArea = False
        self.populate()

        self.setCentralWidget(self.central)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            exit(0)
        if event.key() == Qt.Key_Return:
            if self.first:
                print(self.first, end='')
                exit(0)
        event.accept()

    def edit(self, s):
        self.query = s
        self.timer.stop()
        self.timer.start(DELAY)

    def populate(self):
        self.timer.stop()
        if (self.scrollArea):
            self.scrollArea.deleteLater()
        # Create scroll area and grid
        self.scrollArea = QScrollArea(self.central)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = Contents(self.scrollArea)
        self.gridLayout = TiledLayout(self.scrollAreaWidgetContents)

        # Populate grid
        pat = os.path.join(self.path, "**", f"*{self.query}*.png")
        paths = glob.glob(pat, root_dir=self.path, recursive=True)[0:LIMIT]
        try:
            self.first = paths[0]
        except IndexError:
            self.first = None
        for n, fn in enumerate(paths):
            pixmap = QPixmap(fn)
            label = Tile(self.scrollAreaWidgetContents, self.args, fn, pixmap)
            # label.setFixedSize(THUMB,THUMB)
            label.setScaledContents(True)
            label.setMinimumSize(MINTH,MINTH)
            label.setMaximumSize(THUMB,THUMB)
            label.setPixmap(pixmap.scaled(THUMB,THUMB, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            label.setMargin(INSET)
            label.setStyleSheet(f"background-color: {self.args.matte}")
            self.gridLayout.addWidget(label)
            if not self.scrollAreaWidgetContents.selected:
                self.scrollAreaWidgetContents.select(label)

         # Add scroll area
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.centralLayout.addWidget(self.scrollArea)

def execute():
    parser = argparse.ArgumentParser(description='link a meme')
    parser.add_argument('path',
        metavar='PATH',
        type=str,
        help='load images here'
    )
    parser.add_argument('query',
        metavar='QUERY',
        type=str,
        nargs='?',
        default='',
        help='start with a query'
    )
    parser.add_argument(
        '--fg',
        dest='fg',
        type=str,
        nargs='?',
        default="#5e6fa0",
        help='Foreground color (hex)',
    )
    parser.add_argument(
        '--bg',
        dest='bg',
        type=str,
        nargs='?',
        default="#191919",
        help='Background color (hex)',
    )
    parser.add_argument(
        '--fn',
        dest='fn',
        type=str,
        nargs='?',
        default="Hack, Terminus, monospace",
        help='Font family (CSS-style, like "Hack, Terminus, monospace")',
    )
    parser.add_argument(
        '-p',
        dest='prompt',
        type=str,
        nargs='?',
        default="",
        help='Prompt text to display',
    )
    args = parser.parse_args()

    args.matte = QColor(args.bg).lighter(160).name(QColor.HexRgb)
    fg = QColor(args.fg)
    luma = ((0.299 * fg.red()) + (0.587 * fg.green()) + (0.114 * fg.blue())) / 255
    if luma > 0.5:
        args.hilite = "#000000"
    else:
        args.hilite = "#e0e0e0"


    app = QApplication(sys.argv)
    app.setStyleSheet(f"""
        QMainWindow, QLineEdit,
        QScrollArea QWidget,
        QScrollBar:vertical {{
            color: {args.fg};
            background-color: {args.bg};
        }}
        QLineEdit {{
            font-size: 16px;
            font-weight: bold;
            font-family: {args.fn};
            padding-left: 5px;
        }}
        QLineEdit,
        QScrollArea {{
            border: 0;
        }}
        QScrollBar::handle:vertical {{
            background-color: {args.fg};
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            background-color: {args.bg};
        }}
        Tile {{
            padding: 20px;
            background-color: {args.matte};
        }}
        QMainWindow {{
            margin: 0;
            padding: 0;
        }}
    """)
    window = MainWindow(args)
    window.show()
    #window.activateWindow()
    app.exec()
