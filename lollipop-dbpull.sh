adb connect 172.16.227.160:5555
adb root
adb shell am force-stop com.aoitek.lollipop
sleep 10
adb shell am start -n com.aoitek.lollipop/.MainActivity
sleep 10
adb shell input tap 250 200
sleep 10
adb shell input tap 950 20
sleep 1
adb shell input tap 950 20
sleep 5
adb shell input tap 870 350
sleep 10
rm SleepLog.log
rm lollipop-room
adb pull /data/data/com.aoitek.lollipop/databases/lollipop-room ./lollipop-room
adb pull /data/data/com.aoitek.lollipop/databases/lollipop-room ./lollipop-room-wal
sqlite3 ./lollipop-room 'SELECT * FROM SleepLog ORDER BY timestamp;' > SleepLog.log
tail -n 10 SleepLog.log
