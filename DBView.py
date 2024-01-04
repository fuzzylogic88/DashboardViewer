# DBViewer
#
# A small kiosk-style utility to view webpages from a SFF PC / RPi
#
# Press right arrow key to move to next URL, down arrow key to stop cycle, ESC to exit.

from PyQt5.QtCore import QUrl, QTimer, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QApplication, QShortcut
from PyQt5.QtWebEngineWidgets import QWebEngineView as QWebView
from PyQt5.QtWebEngineWidgets import QWebEngineSettings as QWebSettings
from PyQt5.QtNetwork import *

import platform
import sys

# URL File Locations (one URL per line):
URL_FILE_PATH_WINDOWS = "C:\\DBurl.txt"
URL_FILE_PATH_LINUX = "/home/pi/DBurl.txt"

DEFAULT_DELAY_MS = 15000

globalFPath = ''
urlList = ['']

class Browser(QWebView):
    def __init__(self, urlList):
        super(Browser,self).__init__()
        
        # check platform and establish filepath for URLs.
        current_os = platform.system()
        if current_os == 'Linux':
            self.globalFPath = URL_FILE_PATH_LINUX
        elif current_os == 'Windows':
            self.globalFPath = URL_FILE_PATH_WINDOWS
        
        self.timers = []
        self.urlList = load_url_from_file(self.globalFPath)
        self.current_index = 0

    def load(self,url):
        self.setUrl(QUrl(url))
    
    def load_next_url(self):         
            # move though list of dashboard URLs
        if self.current_index < len(self.urlList):
            url = self.urlList[self.current_index] 
            self.load(QUrl(url))
            self.current_index += 1
        else:
            # start from the beginning of the collection
            self.current_index = 0
        
        # kick off a new timer, and add to collection of timers...
        if self.current_index > 0:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(self.load_next_url)
            timer.start(DEFAULT_DELAY_MS)
            self.timers.append(timer)
        else:
            self.load_next_url()
    
    # Cancels current timer and loads the next URL in the queue
    def skip_timers(self, load_next):
        print("Cancelling active timers")
        for timer in self.timers:
            timer.stop()
            timer.timeout.disconnect()
            timer.deleteLater()
        self.timers.clear()
        
        if (load_next):
            print("Jumping to next URL")
            self.load_next_url()
    
    def adjustTitle(self):
        self.setWindowTitle(self.title())
    
    def userAgentForUrl(self):
        ''' Returns a User Agent that will be seen by the website. '''
        return "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36"
    
    def disableJS(self):
        settings = QWebSettings.globalSettings()
        settings.setAttribute(QWebSettings.JavascriptEnabled, False)

def main():
    app = QApplication(sys.argv)   
    window = Browser(urlList)
    
    # creates a borderless window and displays the content fullscreen
    window.setWindowFlags(Qt.FramelessWindowHint)
    window.showFullScreen()

    # define which keypresses to monitor for
    window.close_shortcut = QShortcut(QKeySequence(Qt.Key_Escape),window)
    window.skip_url_shortcut = QShortcut(QKeySequence(Qt.Key_Right),window)
    window.stop_timers_shortcut = QShortcut(QKeySequence(Qt.Key_Down),window)
    
    # attach our shortcuts to functions to create keyboard event handlers
    window.close_shortcut.activated.connect(window.close)
    window.skip_url_shortcut.activated.connect(lambda: window.skip_timers(True))
    window.stop_timers_shortcut.activated.connect(lambda: window.skip_timers(False))
    
    window.setWindowTitle('Loading...')
    
    # change window title on new connections
    window.titleChanged.connect(window.adjustTitle)
    
    # kick off our URL load-loop
    window.load_next_url()
    sys.exit(app.exec_())

# reads data from filepath established during '__init__'
def load_url_from_file(globalFPath):
    with open(globalFPath, 'r') as file:
        urlList = [line.strip() for line in file.readlines() if line.strip()]
    return urlList

if __name__ == "__main__":
    main()