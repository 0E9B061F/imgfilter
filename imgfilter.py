import sys
import os
import argparse
import hashlib
import glob
import json
import pyperclip
import requests
from threading import Timer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QScrollArea, QVBoxLayout, QLineEdit, QSizePolicy, QLayout
from PySide6.QtCore import Qt, QMargins, QPoint, QRect, QSize, QTimer


BUFFER = 65536 * 2
API = 'https://api.imgur.com/3/image'
HOME = os.path.expanduser("~")
HASHDB = os.path.join(HOME, '.imgfilter.json')
DELAY = 300


class HashDB:
    def __init__(self, path):
        self.path = path
        if os.path.isfile(self.path):
            data = open(self.path, 'r')
            self.data = json.load(data)
        else:
            self.data = {}

    def get(self, hash):
        if hash in self.data:
            return self.data[hash]
        else:
            return False

    def insert(self, hash, link):
        self.data[hash] = link
        self.save()

    def save(self):
        json.dump(self.data, open(self.path, 'w'))

class ImgDB:
    def __init__(self, client_id):
        self.client_id = client_id
        self.params = dict(
            client_id=self.client_id
        )
        self.hashdb = HashDB(HASHDB)

    def link(self, path):
        hash = self.hash(path)
        print(f"HASH: {hash}")
        link = self.hashdb.get(hash)
        if link == False:
            print(f"UPLOADING: {path}")
            link = self.upload(path)
            if link != False:
                self.hashdb.insert(hash, link)
        return link
  
    def hash(self, path):
        md5 = hashlib.md5()
        with open(path, 'rb') as f:
            while True:
                data = f.read(BUFFER)
                if not data:
                    break
                md5.update(data)
        return md5.hexdigest()

    def upload(self, path):
        file = open(path, 'rb')
        files = dict(
            image=(None, file),
            name=(None, ''),
            type=(None, 'file'),
        )
        r = requests.post(API, files=files, params=self.params)
        if (r.status_code == 200):
            data = json.loads(r.text)
            if (data['status'] == 200):
                return data['data']['link']
            else:
                return False
        else:
            return False

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
    def __init__(self, imgdb, parent, path):
        super().__init__(parent)
        self.imgdb = imgdb
        self.path = path

    def mousePressEvent(self, event):
        link = self.imgdb.link(self.path)
        if (link == False):
            print('ERROR: failed getting link')
        else:
            print(f"LINK: {link}")
            pyperclip.copy(link)
            print('Copied link to clipboard.')
        quit(0)

class MainWindow(QMainWindow):
    def __init__(self, imgdb, path, query=''):
        super().__init__()

        self.imgdb = imgdb
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
        for n, fn in enumerate(glob.glob(pat, root_dir=self.path, recursive=True)):
            label = ClickLabel(self.imgdb, self.scrollAreaWidgetContents, fn)
            pixmap = QPixmap(fn)
            label.setFixedSize(300,300)
            label.setPixmap(pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            self.gridLayout.addWidget(label)

         # Add scroll area
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.centralLayout.addWidget(self.scrollArea)


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
args = parser.parse_args()

imgdb = ImgDB('54cd5ba3aa93f4e')
app = QApplication(sys.argv)
window = MainWindow(imgdb, args.path, args.query)
window.show()
app.exec()
