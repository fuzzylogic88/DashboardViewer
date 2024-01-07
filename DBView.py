# DBViewer, Daniel Green
#
# A small kiosk-style utility to view webpages from a SFF PC / RPi
#
# Press right arrow key to move to next URL, down arrow key to stop cycle, ESC to exit.

from PyQt5.QtCore import QUrl, QTimer, Qt
from PyQt5.QtGui import QKeySequence, QFontDatabase, QFont
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QMessageBox, QShortcut
from PyQt5.QtWebEngineWidgets import QWebEngineView as QWebView
from PyQt5.QtNetwork import *

import sys
import os
import re

# File Locations (one item per line):
ContentFilePath = "DBViewContent.txt"
FontFilePath = "fnt.ttf"
DEFAULT_DELAY_MS = 10000

contentList = ['']

class MainWindow(QMainWindow):
    def __init__(self, contentList):
        super(MainWindow,self).__init__()   

        self.webview = QWebView(self)
        # Set up the pause control
        self.SetupLabels()

        self.contentList = load_url_from_file(ContentFilePath)

        if len(self.contentList) == 0:
            self.no_content_label.show()

        self.current_timer = QTimer(self)
        self.remaining_time = 0
        self.timers_are_paused = False
        self.current_index = 0
        
    def SetupLabels(self):
        # Create a layout for the central widget
        layout = QVBoxLayout()

        # Load font from local file to use for labels
        if os.path.exists(FontFilePath):  
            font_id = QFontDatabase.addApplicationFont(FontFilePath)
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            font = QFont(font_family)
        else:
            self.missing_font_error()

        # Create a pause overlay label
        self.pause_label = QLabel("PAUSED", self)
        self.pause_label.setAlignment(Qt.AlignCenter)
        self.pause_label.setFont(font)
        self.pause_label.setStyleSheet("background-color: rgba(64, 222, 251, 128); font-size: 32px;")
        self.pause_label.setFixedSize(150, 60)  # Adjust width and height as needed
        self.pause_label.hide()

        self.no_content_label = QLabel("No content to display!", self)
        self.no_content_label.setAlignment(Qt.AlignCenter)
        self.no_content_label.setFont(font)
        self.no_content_label.setStyleSheet("background-color: rgba(0, 150, 211, 128); font-size: 48px;")
        self.no_content_label.hide()
        
        # Add the layout to the central widget
        central_widget = QWidget()
        central_widget.setLayout(layout)

        # Set up the initial content within the central widget
        self.webview.page().setView(central_widget)
        self.setCentralWidget(self.webview)
    
    def missing_font_error(self):
        app = QApplication(sys.argv)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setText(f'Local font file "{FontFilePath}" not found!')
        msg_box.setWindowTitle("Fatal error")
        msg_box.exec_()
        app.quit()

    def resizeEvent(self, event):
        # Resize the label to match the window size
        self.no_content_label.setGeometry(self.rect())

    def load(self,url):
        self.webview.setUrl(QUrl(url))
    
    def load_next_url(self):         
       
            if (self.current_index < len(self.contentList)):          
                url = self.contentList[self.current_index] 
            
                # differentiate between local files / embedded html, and URLs
                item_is_a_file = os.path.exists(url)           
                if item_is_a_file or url.startswith("<"):
                    self.webview.setHtml(generate_html(url, item_is_a_file), QUrl(f'file:///{url}'))
                else:
                    self.webview.setUrl(QUrl(url))
                self.current_index += 1     

            else:
                # start from the beginning of the collection
                self.current_index = 0

            if not self.current_timer is None:
                if self.current_timer.isActive():
                    return
          
            # Start a new timer
            if self.current_index > 0:
                print(f"Starting new timer with content at index {self.current_index}")
                self.current_timer = QTimer(self)
                self.current_timer.setSingleShot(True)
                self.current_timer.timeout.connect(self.load_next_url)
                self.current_timer.start(DEFAULT_DELAY_MS)
            else:
                self.load_next_url()
        
    # Cancels current timer and loads the next item in the queue
    def navigate_content(self, load_forward): 
        self.pause_label.setVisible(False)      

        if (not load_forward):
            print("Loading previous item")
            if (self.current_index - 2 >= 0):
                self.current_index -= 2
            else:
                self.current_index = len(self.contentList) - 1
        else:
            print("Jumping to next item")

        self.load_next_url()     

    def pause_cycle(self):
        if self.current_timer.isActive():
            print(f'Timer paused with {self.current_timer.remainingTime()}ms remaining')
            self.remaining_time = self.current_timer.remainingTime()
            self.pause_label.setVisible(True)
            self.current_timer.stop()
        else:
            print(f'Timer resumed with {self.remaining_time}ms remaining')
            self.pause_label.setVisible(False)
            self.current_timer.start(self.remaining_time)

    # stops active timer and notes remaining time, supposing we wanted to continue
    def stop_active_timer(self):
        print("Stopping active timers")
        self.current_timer.stop()
        self.current_timer.timeout.disconnect()
        self.current_timer.deleteLater()

    def adjustTitle(self):
        self.setWindowTitle(self.webview.title())

def main():
    app = QApplication(sys.argv)   
    window = MainWindow(contentList)
    window.setWindowTitle('DBView')

    # creates a borderless window and displays the content fullscreen
    #window.setWindowFlags(Qt.FramelessWindowHint)
    #window.showFullScreen()

    # windowed for debug
    window.setGeometry(100, 100, 800, 600)  # Set the desired width and height
    window.show()

    # define which keypresses to monitor for
    window.close_shortcut = QShortcut(QKeySequence(Qt.Key_Escape),window)
    window.next_item_shortcut = QShortcut(QKeySequence(Qt.Key_Right),window)
    window.prev_item_shortcut = QShortcut(QKeySequence(Qt.Key_Left),window)
    window.pause_timer_shortcut = QShortcut(QKeySequence(Qt.Key_Down),window)
    
    # attach our shortcuts to functions to create keyboard event handlers
    window.close_shortcut.activated.connect(window.close)
    window.next_item_shortcut.activated.connect(lambda: window.navigate_content(True))
    window.prev_item_shortcut.activated.connect(lambda: window.navigate_content(False))
    window.pause_timer_shortcut.activated.connect(window.pause_cycle)
    
    # change window title on new connections
    window.webview.titleChanged.connect(window.adjustTitle)
    
    # kick off our content load-loop if we have content to show
    if len(window.contentList) > 0:
        window.load_next_url()
    sys.exit(app.exec_())

# reads data from filepath established during '__init__'
def load_url_from_file(fpath):
    with open(fpath, 'r') as file:
        contentList = [line.strip() for line in file.readlines() if line.strip()]
    return contentList

def generate_html(item, item_is_a_file):
    raw_html = ''

    # Image files
    if (item_is_a_file):       
        image_path = 'file:///'
        image_path +=  os.path.abspath(item)
        
        raw_html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                            margin: 0;
                            background-color: #202248;
                            overflow: hidden;
                    }}
                    
                    img {{
                        width: 100vw;
                        height: 100vh;
                        object-fit: contain;
                    }}
                </style>
            </head>
            <body>
                <img src="{image_path}" alt="BigImage">
            </body>
            </html>
            '''             
    # embedded HTML    
    else:
        raw_html = '<html><head><meta charset="utf-8" /><body>'
        raw_html += item
        raw_html += '</body></html>'

        # Regular expression to find width and height attributes
        pattern = re.compile(r'width="(\d+)" height="(\d+)"')

        # Replace width and height attributes with fullscreen style attribute
        raw_html = re.sub(pattern, r'style="min-width: 100%; min-height: 100vh;"', raw_html)   
    return raw_html
  
if __name__ == "__main__":
    main()