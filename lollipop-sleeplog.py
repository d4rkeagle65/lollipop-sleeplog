import os
import time
import sqlite3
import requests
import json
import datetime
import csv
import pytz
import logging
import getopt, sys
from dotenv import load_dotenv
from adb_shell.adb_device import AdbDeviceTcp

load_dotenv()

ANDROID_VM_IP=os.getenv('ANDROID_VM_IP')
ANDROID_VM_PORT=os.getenv('ANDROID_VM_PORT')
BABYBUDDY_APIKEY=os.getenv('BABYBUDDY_APIKEY')
BABYBUDDY_URL=os.getenv('BABYBUDDY_URL')
LOGLEVEL=os.getenv('LOGLEVEL')

argumentList = sys.argv[1:]
options = ""
long_options = ["no-refresh"]
dir_path = os.path.dirname(os.path.realpath(__file__))
logging.basicConfig(filename=dir_path + "/data/lollipop-sleeplog-log.log",
                    format='%(asctime)s - %(levelname)s: %(message)s',
                    filemode='a',
                    level=LOGLEVEL)

logger = logging.getLogger()

def adb_tap(device, x, y, sleep):
    logger.debug("Sending Device Tap: x:[" + str(x) + "] y:[" + str(x) + "]")
    device.shell('input tap ' + str(x) + ' ' + str(y), transport_timeout_s=30)
    logger.debug("Sleeping for Seconds:[" + str(sleep) + "]")
    time.sleep(sleep)

def reload_sleeplog():
    logger.info("Connecting to Android Device")
    android_device = AdbDeviceTcp(ANDROID_VM_IP, ANDROID_VM_PORT, default_transport_timeout_s=30)
    android_device.connect()
    
    logger.debug("Setting ADB Shell to Root")
    android_device.root()

    logger.info("Killing the Lollipop App")
    android_device.shell('am force-stop com.aoitek.lollipop', transport_timeout_s=30)
    logger.debug("Sleeping for Seconds:[5]")
    time.sleep(5)
    logger.info("Restarting the Lollipop App")
    android_device.shell('am start -n com.aoitek.lollipop/.MainActivity', transport_timeout_s=30)
    logger.debug("Sleeping for Seconds:[15]")
    time.sleep(15)
    logger.info("Clicking into the Camera Feed")
    adb_tap(android_device,250,200,10)
    logger.info("Opening the Additional Information Section")
    adb_tap(android_device,950,20,1)
    adb_tap(android_device,950,20,5)
    logger.info("Refreshing the Sleep Log Database")
    adb_tap(android_device,870,340,15)
    logger.info("Done Refreshing the Sleep Log")

    logger.info("Downloading the Database")
    android_device.pull("/data/data/com.aoitek.lollipop/databases/lollipop-room",dir_path + "/data/lollipop-room", transport_timeout_s=30)
    logger.info("Killing the Lollipop App")
    android_device.shell('am force-stop com.aoitek.lollipop', transport_timeout_s=30)

def get_lastSleep():
    url = "https://" + BABYBUDDY_URL + "/api/sleep/?limit=1"
    logger.debug("Querying API for The Last Sleep Record")
    response = requests.get(url, headers={"Authorization": "Token " + BABYBUDDY_APIKEY, "Content-Type": "application/json"})
    logger.debug("API Response: " + str(response.json()))
    endTime = response.json()['results'][0]['end']
    logger.debug("Converting To Unix Timestamp: [" + str(endTime) + "]")
    endTime_obj = datetime.datetime.strptime(endTime, "%Y-%m-%dT%H:%M:%S%z")
    return int(endTime_obj.timestamp())

def get_newSleepFromDB(lastSleep):
    logger.debug("Connecting to sqlite3 Database")
    db = sqlite3.connect(dir_path + "/data/lollipop-room")
    lastSleep = lastSleep * 1000
    sleepLog = db.execute("SELECT * FROM SleepLog WHERE timestamp > " + str(lastSleep) + " ORDER BY timestamp").fetchall()
    logger.debug("New Sleep Logs: [" + str(sleepLog) + "]")
    return sleepLog

def get_newSleepFromFile():
    sleepLog = []
    with open(dir_path + "/data/sleep.log") as csvfile:
        spamreader = csv.reader(csvfile, delimiter='|', quotechar=None)
        for row in spamreader:
            sleepLog.append(row)
    return sleepLog

def post_newSleepFromDB(sleepStartTS, sleepEndTS):
    logger.debug("Converting Timestamps")
    new_sleepStartTS = datetime.datetime.fromtimestamp(int(sleepStartTS) / 1000, datetime.timezone.utc).astimezone(pytz.timezone("America/Detroit")).strftime("%Y-%m-%dT%H:%M:%S")
    logger.debug("New Start Timestamp: [" + str(new_sleepStartTS) + "]")
    new_sleepEndTS = datetime.datetime.fromtimestamp(int(sleepEndTS) / 1000, datetime.timezone.utc).astimezone(pytz.timezone("America/Detroit")).strftime("%Y-%m-%dT%H:%M:%S")
    logger.debug("New End Timestamp: [" + str(new_sleepEndTS) + "]")
    url = "https://" + BABYBUDDY_URL + "/api/sleep/"
    data = {'child': 1,
            'start': new_sleepStartTS,
            'end': new_sleepEndTS,
            'tags': ['lollipop']}
    logger.debug("Sending POST to API")
    response = requests.post(url, 
                             headers={"Authorization": "Token " + BABYBUDDY_APIKEY, "Content-Type": "application/json"},
                             json=data)
    logger.debug("API Response: [" + str(response.text) + "]")

refresh = True
try:
    arguments, values = getopt.getopt(argumentList, options, long_options)
    for currentArgument, currentValue in arguments:
        if currentArgument in ("--no-refresh"):
            refresh = False

except getopt.error as err:
    logger.error(str(err))

logger.info("Starting a new run of lollipop-sleeplog.py")
if refresh:
    logger.info("Reloading the Sleep Log")
    reload_sleeplog()
else:
    logger.info("Sleep Log Refresh Disabled")
logger.info("Getting the Last Sleep End Time")
lastSleep = get_lastSleep()
logger.info("Last Sleep End Time: [" + str(lastSleep) + "]")
logger.info("Getting New Sleep Entires from DB")
sleepLog = get_newSleepFromDB(lastSleep)
#sleepLog = get_tempSleep()

sleepWindowsToAdd = []
discoveredSleepTS = False
sleepStartTS = 0
sleepEndTS = 0
notSleep = 0
if len(sleepLog) > 0:
    logger.debug("Sleeplogs to Parse: [" + str(len(sleepLog)) + "]")
    for x in range(len(sleepLog)):
        logger.debug("Checking: " + str(sleepLog[x]))
        if sleepLog[x][2] == "sleep" and sleepStartTS == 0 and int(sleepLog[x][1]) > lastSleep * 1000:
            if discoveredSleepTS == False:
                discoveredSleepTS = True
            sleepStartTS = sleepLog[x][1]
            logger.debug("Discovered Sleep Window, StartTS: [" + str(sleepStartTS) + "]")
        if sleepLog[x][2] != "sleep" and int(sleepLog[x][1]) > 0 and sleepStartTS != 0:
            sleepEndTS = sleepLog[x][1]
            logger.debug("Discovered Sleep Window Ending, EndTS: [" + str(sleepEndTS) + "]")
            sleepWindowsToAdd.append([sleepStartTS,sleepEndTS])
            sleepEndTS = 0
            sleepStartTS = 0

if len(sleepWindowsToAdd) > 0:
    logger.debug("Sleep Windows to Add: [" + str(len(sleepWindowsToAdd)) + "]")
    for y in range(len(sleepWindowsToAdd)):
        logger.info("Adding Sleep Window [" + str(y) + "]-[(" + str(sleepWindowsToAdd[y][0]) + "-" + str(sleepWindowsToAdd[y][1]) + ")]")
        post_newSleepFromDB(sleepWindowsToAdd[y][0],sleepWindowsToAdd[y][1])

logger.info("Ending the run of lollipop-sleeplog.py")