# DBViewer, Daniel Green
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

import sys
import os

# File Locations (one item per line):
ContentFilePath = "DBViewContent.txt"
DEFAULT_DELAY_MS = 15000

contentList = ['']

class Browser(QWebView):
    def __init__(self, contentList):
        super(Browser,self).__init__()
        
        self.timers = []
        self.contentList = load_url_from_file(ContentFilePath)
        self.current_index = 0

    def load(self,url):
        self.setUrl(QUrl(url))
    
    def load_next_url(self):         
        # move though list of items, selecting new content by index
        if self.current_index < len(self.contentList):
            url = self.contentList[self.current_index] 
            
            # differentiate between local files / embedded html, and URLs
            item_is_a_file = os.path.exists(url)           
            if item_is_a_file or url.startswith("<"):
                self.setHtml(generate_html(url, item_is_a_file),QUrl('file:///'))
            else:
                self.setUrl(QUrl(url))
                
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
    
    # Cancels current timer and loads the next item in the queue
    def skip_timers(self, load_next):
        print("Cancelling active timers")
        for timer in self.timers:
            timer.stop()
            timer.timeout.disconnect()
            timer.deleteLater()
        self.timers.clear()
        
        if (load_next):
            print("Jumping to next item")
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
    window = Browser(contentList)
    
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
    
    # kick off our content load-loop
    window.load_next_url()
    sys.exit(app.exec_())

# reads data from filepath established during '__init__'
def load_url_from_file(fpath):
    with open(fpath, 'r') as file:
        contentList = [line.strip() for line in file.readlines() if line.strip()]
    return contentList

def generate_html(item, item_is_a_file):
    raw_html = ''

    # images
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
    
    return raw_html
  
if __name__ == "__main__":
    main()