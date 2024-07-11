I use a Lollipop Baby Camera along with Baby Buddy, and wanted to get the sleep data from the camera app into Baby Buddy. 

I discovered that Lollipop stores a sqlite3 database in their Android data directory, and I can easily read it as it is a sqlite3 database.

This code is messy but works for me. I will clean it up in the future. I have this running hourly w/ a crontab entry.

In setting this up you need to have some sort of rooted Android device or VM with the Lollipop app installed and logged into. The app does not have many intents, so I had to use adb touches to open a specific section of the app which queries the camera/cloud for the updated sleep data. Depending on you setup you will probably need to update those X and Y values.

.env file should have
 - BABYBUDDY_URL
 - BABYBUDDY_APIKEY
 - ANDROID_VM_IP
 - ANDROID_VM_PORT
 - LOGLEVEL
 - TIMEZONE
