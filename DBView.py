# DBViewer, Daniel Green
#
# A small kiosk-style utility to view webpages from a SFF PC / RPi
#
# Press right arrow key to move to next URL, down arrow key to stop cycle, ESC to exit.
# Press up arrow to enter URL manually (helpful for SSO auth)

# requires: qt6-wayland, python3-pyqt6.qtwebengine, python3-pyqt6


from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtWebEngineWidgets import *
from PyQt6.QtWebEngineCore import *

import sys
import os
import re

# File Locations, CASE SENSITIVE!:
ContentFilePath = "DBViewContent.txt"
FontFilePath = "fnt.ttf"
DEFAULT_DELAY_MS = 60000

contentList = ['']

class MainWindow(QMainWindow):
    def __init__(self, contentList):
        super(MainWindow, self).__init__()   

        self.webview = QWebEngineView(self)
        self.setup_web_engine_profile()
        self.qwebpage = QWebEnginePage(self.profile)
        self.webview.setPage(self.qwebpage)

        self.setup_labels()

        self.last_accessed_content = ""
        self.current_timer = QTimer(self)
        self.remaining_time = 0
        self.timers_are_paused = False
        self.current_index = 0

    def setup_web_engine_profile(self):
        self.profile = QWebEngineProfile('WebEngineDefaultProfile')
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        self.profile.setPersistentStoragePath(os.path.abspath('data'))
        self.profile.setCachePath(os.path.abspath('data'))

        self.profile.cookieStore().cookieAdded.connect(self.on_cookie_added)

    def on_cookie_added(self, cookie):
        print("Cookie added:", cookie.name(), cookie.value())

    def setup_labels(self):
        # Create a layout for the central widget
        layout = QVBoxLayout()

        # Load font from local file to use for labels
        font = self.load_font_from_file()

        # Create a pause overlay label
        self.pause_label = QLabel("PAUSED", self)
        self.pause_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pause_label.setFont(font)
        self.pause_label.setStyleSheet("background-color: rgba(64, 222, 251, 128); font-size: 48px;")
        self.pause_label.setFixedSize(175, 80)  # Adjust width and height as needed
        self.pause_label.hide()

        self.main_label = QLabel("", self)
        self.main_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_label.setFont(font)
        self.main_label.setStyleSheet("background-color: rgba(0, 150, 211, 128); font-size: 64px;")
        self.main_label.hide()

        # Add the layout to the central widget
        central_widget = QWidget()
        central_widget.setLayout(layout)

        # Set up the initial content within the central widget
        self.setCentralWidget(central_widget)
    
        
    def load_font_from_file(self):
        if os.path.exists(FontFilePath):
            font_id = QFontDatabase.addApplicationFont(FontFilePath)
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            return QFont(font_family)
        else:
            self.missing_font_error()
            sys.exit(1)

    def missing_font_error(self):
        app = QApplication(sys.argv)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setText(f'Local font file "{FontFilePath}" not found!')
        msg_box.setWindowTitle("Fatal error")
        msg_box.exec()
        app.quit()

    def missing_content_list_error(self):
        app = QApplication(sys.argv)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setText(f'Local content list "{ContentFilePath}" not found!')
        msg_box.setWindowTitle("Fatal error")
        msg_box.exec()
        app.quit()

    def resizeEvent(self, event):
        # Resize the label to match the window size
        self.main_label.setGeometry(self.rect())

    def show_text_input_dialog(self):
        print("Showing URL entry dialog!")
        input_dialog = QInputDialog(self)
        text, ok = input_dialog.getText(self, "Prompt", "Enter URL / Embedded HTML:")

        if ok and text:
            if self.current_timer.isActive():
                self.stop_active_timer()
            self.load_next_url(text)
    
    def start_new_timer(self, ms):
            print(f"Starting new timer with content at index {self.current_index} for {DEFAULT_DELAY_MS}ms.")
            self.current_timer = QTimer(self)
            self.current_timer.setSingleShot(True)
            self.current_timer.timeout.connect(lambda: self.load_next_url(None))
            self.current_timer.start(ms)
            print(f"Current timer has {self.current_timer.remainingTime()}ms left")

    def load_next_url(self, url):   
        self.user_has_defined_source = url is not None  

       # Cycling through collection as usual
        if url is None:
            self.load_url_from_file(ContentFilePath) # only reload data if no URL was defined.
            if (self.current_index < len(self.contentList)):
                    url = self.contentList[self.current_index] 
                    self.current_index += 1   

            # Start from the beginning of the collection if we've reached the end
            else:
                self.current_index = 0

        # differentiate between local files / embedded html, and URLs
        if url is not None:
            item_is_a_file = os.path.exists(url)                
            if item_is_a_file or url.startswith("<"):
                self.webview.setHtml(generate_html(url, item_is_a_file), QUrl.fromLocalFile(url))
            else:
                self.qwebpage.load(QUrl(url))
                self.setCentralWidget(self.webview)   

        # If a timer is running and we've not manually defined a source
        # wait for it to complete before making a new one.
        if not self.current_timer is None and not self.user_has_defined_source:
            if self.current_timer.isActive():
                return
          
        # Start a new timer otherwise
        if self.current_index > 0 or self.user_has_defined_source:
            self.start_new_timer(DEFAULT_DELAY_MS)

            self.last_accessed_content = self.webview.url().toString();
            print(f"Last accessed content saved: {self.last_accessed_content}")
            
        else:
            self.load_next_url(None)       

    # Cancels current timer and loads the next item in the queue
    def navigate_content(self, load_forward):
        self.pause_label.setVisible(False)      
        self.stop_active_timer()

        if (not load_forward):
            print("Loading previous item")
            if (self.current_index - 2 >= 0):
                self.current_index -= 2
            else:
                self.current_index = len(self.contentList) - 1
        else:
            if self.current_index == len(self.contentList):
                self.current_index = 0
            print("Jumping to next item") 
        self.load_next_url(None)

    def pause_cycle(self):
        if self.current_timer.isActive():
            print(f'Timer paused with {self.current_timer.remainingTime()}ms remaining')
            self.remaining_time = self.current_timer.remainingTime()
        else:
            print(f'Timer resumed with {self.remaining_time}ms remaining')

        self.pause_label.setVisible(not self.pause_label.isVisible())
        self.current_timer.stop() if self.current_timer.isActive() else self.current_timer.start(self.remaining_time)

    # stops active timer and notes remaining time, supposing we wanted to continue
    def stop_active_timer(self):
        print("Stopping active timers")
        self.current_timer.stop()
        self.current_timer.timeout.disconnect()
        self.current_timer.deleteLater()

    def adjustTitle(self):
        self.setWindowTitle(self.webview.title())
        print(f"New window title is: {self.windowTitle()}")
        if self.webview.title() == "about:blank":
            self.main_label.setText("No content to display.\nWaiting...")
            self.main_label.show()
        else:
            self.main_label.hide()

        # reads data from filepath established during '__init__'
    def load_url_from_file(self, fpath):
        if (os.path.exists(fpath)):
            try:
                print("Updating data in content list")
                with open(fpath, 'r') as file:
                    self.contentList = [line.strip() for line in file.readlines() if line.strip()]
                if len(self.contentList) == 0 and not self.user_has_defined_source:
                    print("No data in file! Deferring to last-accessed content...")
                    if (self.last_accessed_content != ""):
                        self.load_next_url(self.last_accessed_content)
                    else:
                        self.main_label.setText("No content to display.\nWaiting...")
                        self.main_label.show()
                        self.start_new_timer(1000)

            except:
                # if it fails, try again after a short delay
                print("Content load failed! Deferring to last-accessed content...")
                if (self.last_accessed_content != ""):
                    self.load_next_url(self.last_accessed_content)
                else:
                    self.main_label.setText("Content file failed to load.\nWaiting...")
                    self.main_label.show()
                    self.start_new_timer(1000)

        else:
            print("Content file inaccessible or missing!")
            exit(0)

    def closeEvent(self, event):
        self.webview.setPage(None)
        del self.qwebpage
        self.profile.deleteLater()
            
def main():
    app = QApplication(sys.argv)   
    window = MainWindow(contentList)
    window.setWindowTitle('DBView')

    # creates a borderless window and displays the content fullscreen
    #window.setWindowFlags(Qt.FramelessWindowHint)
    #window.showFullScreen()

    # windowed for debug
    window.setGeometry(100, 100, 800, 600)

    window.show()

    window.webview.titleChanged.connect(window.adjustTitle)
    
    window.close_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape),window)
    window.manual_nav = QShortcut(QKeySequence(Qt.Key.Key_Up),window)

    window.close_shortcut.activated.connect(window.close)
    window.manual_nav.activated.connect(window.show_text_input_dialog)

    window.next_item_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Right),window)
    window.prev_item_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Left),window)
    window.pause_timer_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Down),window)

    window.next_item_shortcut.activated.connect(lambda: window.navigate_content(True))
    window.prev_item_shortcut.activated.connect(lambda: window.navigate_content(False))
    window.pause_timer_shortcut.activated.connect(window.pause_cycle)

    # kick off our content load-loop
    window.load_next_url(None)
    sys.exit(app.exec())

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
                            background-color: #000000;
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
