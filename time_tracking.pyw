import win32process
import win32gui
import wmi
import time
from datetime import datetime, date
from pywinauto import Application

from pymongo import MongoClient
from bson.objectid import ObjectId


LOG_FILE = 'C:/Users/48509/Desktop/RealTimeTrackApp/errors.log'

CILENT = MongoClient('localhost', 27017)
DB = CILENT['time_tracker']
TIME_ENTRY_COLLECTION = DB['time_entry']

WMI = wmi.WMI()

SLEEP_TIME = 10
SLEEP_TIME_LIMIT = 10


def is_computer_sleeping(curr_time, last_time):
    return last_time and (curr_time - last_time) > (SLEEP_TIME + SLEEP_TIME_LIMIT)


def serialize_time(time):
    return time and datetime.fromtimestamp(time).strftime('%H:%M:%S')


def get_date_from_time(time):
    return time and date.fromtimestamp(time)


def get_time_from_curr_date():
    return round(datetime.timestamp(datetime.combine(datetime.now(), datetime.now().min.time())))


def is_date_change(curr_time, last_time):
    return ( 
        last_time and 
        get_date_from_time(curr_time) != get_date_from_time(last_time)
    )


def get_serialized_date():
    return datetime.now().strftime('%Y-%m-%d')


def calculate_total_time(curr_time, start_time):
    return round(curr_time - start_time)


def add_new_entry(curr_app, curr_app_path, curr_time, start_time):
    return TIME_ENTRY_COLLECTION.insert_one({
        'name' : curr_app,
        'path' : curr_app_path,
        'date': get_serialized_date(),
        'start_time' : serialize_time(start_time),
        'stop_time' : serialize_time(curr_time),
        'total': calculate_total_time(curr_time, start_time)
    }).inserted_id


def update_entry(curr_time, time_to_add, last_inserted_id):
    TIME_ENTRY_COLLECTION.update_one(
        {'_id' : ObjectId(last_inserted_id)},
        {   '$set': {'stop_time' : serialize_time(curr_time)},
            '$inc': {'total': time_to_add}
        }
    )

def error_handling(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            with open(LOG_FILE, 'a') as file:
                file.write(str(datetime.now()))
                file.write('\t')
                file.write(str(func.__name__))
                file.write('\t')
                file.write(str(exc))
                file.write('\n')
            return None
        except:
            with open(LOG_FILE, 'a') as file:
                file.write(str(datetime.now()))
                file.write('\t')
                file.write('Unknown Error')
                file.write('\n')
            return None
            
    return wrapper


@error_handling
def get_app_path(hwnd):
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    proc = WMI.query('SELECT ExecutablePath FROM Win32_Process WHERE ProcessId = %s' % str(pid))[0]
    return proc.ExecutablePath


@error_handling
def get_app_name(hwnd):
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    proc = WMI.query('SELECT Name FROM Win32_Process WHERE ProcessId = %s' % str(pid))[0]
    return proc.name


@error_handling
def get_chrome_url():
    app = Application(backend='uia')
    app.connect(title_re=".*Chrome.*", found_index=0)
    
    elem_name="Address and search bar"
    dlg = app.top_window()
    url = dlg.child_window(title=elem_name, control_type="Edit").get_value()
    
    return url.split('/')[0]


def get_firefox_url():
    app = Application(backend='uia')
    app.connect(title_re=".*Firefox.*", found_index=0)
    
    elem_name="Search with Bing or enter address"
    dlg = app.top_window()
    url = dlg.child_window(title=elem_name, control_type="Edit").get_value()
    
    return url


def get_curr_app():
    hwnd = win32gui.GetForegroundWindow()
    
    app_name = get_app_name(hwnd)
    if app_name == 'chrome.exe':
        app_name = get_chrome_url()
    
    app_path = get_app_path(hwnd)
    
    return app_name, app_path


class TimeTracer():
    def __init__(self):
        self._initial_state()
    
    def _initial_state(self):
        self.last_time = None
        self.last_app = None
        self.last_inserted_id = None

    def run(self):
        while True:
            curr_time = time.time()
            curr_app, curr_app_path = get_curr_app()
            day_change = is_date_change(curr_time, self.last_time)

            if is_computer_sleeping(curr_time, self.last_time):
                self._handle_computer_sleeping()
            
            elif self.last_app != curr_app or day_change:
                self._handle_add_new_entry(curr_app, curr_app_path, curr_time, day_change)

            else:
                self._handle_update_entry(curr_time)
  
            time.sleep(SLEEP_TIME)
            self.last_time = curr_time
            self.last_app = curr_app


    def _handle_computer_sleeping(self):
        self._initial_state()

    def _handle_add_new_entry(self, curr_app, curr_app_path, curr_time, day_change):
        if day_change:
            self.last_time = get_time_from_curr_date()

        if curr_app and self.last_time:
            self.last_inserted_id = add_new_entry(curr_app, curr_app_path, curr_time, self.last_time)

    def _handle_update_entry(self, curr_time):
        update_entry(curr_time, SLEEP_TIME, self.last_inserted_id)


if __name__ == '__main__':
    time_tracker = TimeTracer()
    time_tracker.run()