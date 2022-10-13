import sys
import os
import glob
import argparse
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QScrollArea, QVBoxLayout, QLineEdit, QSizePolicy, QLayout
from PySide6.QtCore import Qt, QMargins, QPoint, QRect, QSize, QTimer


DELAY = 250
THUMB = 300
LIMIT = 50

class FlowLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

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
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())

        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._item_list:
            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal
            )
            layout_spacing_y = style.layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical
            )
            space_x = spacing + layout_spacing_x
            space_y = spacing + layout_spacing_y
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()

class ClickLabel(QLabel):
    def __init__(self, parent, path):
        super().__init__(parent)
        self.path = path

    def mousePressEvent(self, event):
        print(self.path, end='')
        quit(0)

class MainWindow(QMainWindow):
    def __init__(self, path, query=''):
        super().__init__()

        self.path = path
        self.query = query

        self.setLayoutDirection(Qt.LeftToRight)

        # Main widget and its layout
        self.central = QWidget(self)
        self.centralLayout = QVBoxLayout(self.central)

        # Create and add line input
        self.lineEdit = QLineEdit(self.central)
        self.lineEdit.insert(self.query)
        self.lineEdit.textChanged[str].connect(self.edit)
        self.centralLayout.addWidget(self.lineEdit)

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
        self.scrollAreaWidgetContents = QWidget()
        self.gridLayout = FlowLayout(self.scrollAreaWidgetContents)

        # Populate grid
        pat = os.path.join(self.path, "**", f"*{self.query}*.png")
        paths = glob.glob(pat, root_dir=self.path, recursive=True)[0:LIMIT]
        try:
            self.first = paths[0]
        except IndexError:
            self.first = None
        for n, fn in enumerate(paths):
            label = ClickLabel(self.scrollAreaWidgetContents, fn)
            pixmap = QPixmap(fn)
            label.setFixedSize(THUMB,THUMB)
            label.setPixmap(pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            self.gridLayout.addWidget(label)

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
        default="#9e9fd2",
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
    args = parser.parse_args()

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
    """)
    window = MainWindow(args.path, args.query)
    window.show()
    app.exec()
