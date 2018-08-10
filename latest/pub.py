#!/usr/bin/python
import zmq
import time
import json 
import RPi.GPIO as GPIO
import os
import signal
import datetime
import logging

GPIO.setmode(GPIO.BCM)
# Globals used holding values for display
CurrentSpeed   = 0
CurrentCadence = 0
trip_distance  = 0         # Distance travelled during this trip
totalDistance  = 0         # Distance travelled by cycle during the life time
currentTime    = "Not Set" # Current time to be displayed by Clock
duration       = 0         # Duration of the trip 
localtime      =   time.localtime(time.time()) # Current Local Time 
tripStartTime  =   time.localtime(time.time())
g_logFile   = "pub.log"

# Global for calculating speed  and Cadence RPM
# Circumference 2.23 meters
# @ 40 km hour  6.22 rotation per sec
# @ 20 km hour  3.11 rotation per sec
# @ 10 km hour  1.5 rotation per sec

speed_pulse         = 0 
cadence_pulse       = 0
TIME_DELTA_SPEED    = 2
CIRCUMFERENCE       = 2.09
TIME_DELTA_CADENCE  = 10 
SENSOR_IDLE_TIME    = 5

bikeStatus = "Stopped"
lastTimePulseReceived = 0 # Last time when sensor send a pulse.
DATA_SET_SAVE_PERIOD = 60
speedInKmPerHr = 0

speed_calc_start_time = int(time.time())
cadence_calc_start_time = int(time.time())
os.chdir("/home/pi/html/cyclo")

GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# GPIO 23 and 24 set up as an input, pulled down, connected to 3V3 on button press
# now we'll define two IST  functions
# these will run in another thread when our events are detected

def StartLogging():
     global g_logFile
     now = datetime.datetime.now()
     today = now.strftime("%d-%b-%Y")
     g_logFile = "Classify_Log-" + today + ".log"
     #Reconfigure logging again, this time with a file.
     logging.basicConfig(format='%(asctime)s %(message)s',
                           filename=g_logFile, 
                           level=logging.INFO)
     return 
def SaveDataSet(signum,frame):
    global CurrentCadence
    global speedInKmPerHr
    global localtime
    global tripStartTime 

    today     = datetime.date.today()
    hr        = localtime.tm_hour
    min       = localtime.tm_min
    sec       = localtime.tm_sec

    fileName = str(today) 
    logging.info('Start:SaveDataSet')
    logging.info(localtime)
    logging.info(today)

    record = open(fileName,'a') # File opened
    # format the time, Cadence and Speed into string 
    recordString = str(hr) +  '_' + str(min) +  '_' + str(sec) 
    recordString = recordString + ' ; '+ str(CurrentCadence) + ' ; ' 
    recordString = recordString + str(speedInKmPerHr) + "\n"

    record.write(recordString) # Data Written
    record.close()             # File Closed
    logging.info('End:SaveDataSet')
    return


def WatchDog():
    global bikeStatus
    global lastTimePulseReceived
    logging.info('Start:WatchDog')
    timeNow = int(time.time())
    diff = timeNow - lastTimePulseReceived
    logMsg = "Current Time difference is : " + str(diff) 
    if diff  > SENSOR_IDLE_TIME : # if cycle is stopped for more than 5 sec
        CurrentCadence = 0  # show that cadence is zero
        CurrentSpeed   = 0  # show that speed is zero
        bikeStatus = "Stopped"

    logging.info('End:WatchDog')
    return

def Speed_Sensor_ISR(channel):
    global trip_distance 
    global speed_pulse
    global TIME_DELTA_SPEED
    global CIRCUMFERENCE
    global speed_calc_start_time 
    global cadence_calc_start_time 
    global CurrentSpeed 
    global totalDistance
    global bikeStatus
    global duration
    global lastTimePulseReceived

    lastTimePulseReceived = int(time.time())
    bikeStatus            = "Moving"
    speed_pulse           = speed_pulse + 1
    timeNow               = int(time.time())

    timeDelta = timeNow - speed_calc_start_time
    if timeDelta  > TIME_DELTA_SPEED:
       deltaDistance = CIRCUMFERENCE * speed_pulse 
       trip_distance = trip_distance + deltaDistance
       speed_calc_start_time = timeNow
       CurrentSpeed = deltaDistance/timeDelta
       totalDistance = totalDistance + deltaDistance
       speed_pulse = 0
       duration = duration + timeDelta
       

def Cadence_Sensor_ISR(channel):
    global cadence_pulse
    global cadence_calc_start_time
    global CurrentCadence
    cadence_pulse = cadence_pulse + 1
    timeNow = int(time.time())
    timeDelta = timeNow - cadence_calc_start_time
    if timeDelta  > TIME_DELTA_CADENCE:
       CurrentCadence = cadence_pulse * 6 # for 60 secs
       cadence_calc_start_time = timeNow 
       cadence_pulse =  0



# when a falling edge is detected on port 17, regardless of whatever
# else is happening in the program, the function my_callback will be run
GPIO.add_event_detect(23, GPIO.FALLING, 
                      callback=Speed_Sensor_ISR, 
                      bouncetime=300)

# when a falling edge is detected on port 23, regardless of whatever
# else is happening in the program, the function my_callback2 will be run
# 'bouncetime=300' includes the bounce control written into interrupts2a.py
GPIO.add_event_detect(24, GPIO.FALLING, 
                      callback=Cadence_Sensor_ISR, 
                      bouncetime=300)



# ZeroMQ Context
context = zmq.Context()

# Define the socket using the "Context"
sock = context.socket(zmq.REP)
sock.bind("tcp://127.0.0.1:5680")

# *********************************
# Create a watch dog timer for 5 sec to monitor 
# whether cycle is running or not
# if not running reset all parameters to ZERO
# WatchDog is the name of the call back function 
# that will be executed 
# *********************************
#signal.signal(signal.SIGALRM,WatchDog)
#init = time.time()
#signal.setitimer(signal.ITIMER_REAL,5,6)
# end of watch dog

# *********************************
# Create Watch dog time for 60 secs
# ***********************************

signal.signal(signal.SIGALRM,SaveDataSet)
init = time.time()
signal.setitimer(signal.ITIMER_REAL,5,DATA_SET_SAVE_PERIOD)

# *************************************
# End  watch dog for saving data
# *************************************
StartLogging()
logging.info('Started')
root_logger = logging.getLogger()

tripStartTime =  time.localtime(time.time())
while True:
    # This is a waiting call 
    message = sock.recv()
    if message == "ResetTrip":
       CurrentSpeed = 0
       CurrentCadence = 0
       trip_distance = 0
       speedInKmPerHr = 0
       distanceInKm   = 0
       bikeStatus = "Stopped"
       duration = 0
       tripStartTime =  time.localtime(time.time())
       json_string = json.dumps({'Speed': speedInKmPerHr,
                                  'Cadence': CurrentCadence,
                                  'Distance': distanceInKm,
                                  'TotalDistance':totalDistanceInKm,
                                  'Status':bikeStatus,
                                  'Time':currentTime,
                                  'Duration':duration})
       sock.send(json_string)

    elif message == "Shutdown":
       bikeStatus = "Shutdown"
       json_string = json.dumps({'Speed': speedInKmPerHr,
                                  'Cadence': CurrentCadence,
                                  'Distance': distanceInKm,
                                  'TotalDistance':totalDistanceInKm,
                                  'Status':bikeStatus,
                                  'Time':currentTime,
                                  'Duration':duration})
       # perform shutdown
       # save all data
       sock.send(json_string)
       os.system('sudo shutdown now') 
    else:
        # Break down  current time  into hours:Minutes:Seconds
        # then format into a string
        localtime = time.localtime(time.time()) 
        logging.info('Main: Updating local time:')
        logging.info(localtime)
        hr = localtime.tm_hour
        min = localtime.tm_min
        sec = localtime.tm_sec
        currentTime = str(hr) + ":" + str(min) + ":" + str(sec) 
        # End of breaking down duration and making into to a string
   
        # Convert Speed which is in meters per to km/hour 
        speedInKmPerHr = round((CurrentSpeed * 3.6),1)

        # Distance is in meters convert it into km 
        distanceInKm   = round(trip_distance/1000,1)
        totalDistanceInKm = round(totalDistance/1000,1)

        # Duration is in Seconds
        # Break downs duration into hours:Minutes:Seconds
        minutes = duration / 60;
        seconds = duration % 60;
        hours = minutes / 60;
        minutes = minutes % 60;
        # variables hours, minites and seconds are formatted into a string
        durationString  = str(hours) + ":" + str(minutes) + ":" + str(seconds)  
        # End of breaking down duration and making into to a string

        json_string = json.dumps({'Speed': speedInKmPerHr,
                                  'Cadence': CurrentCadence,
                                  'Distance': distanceInKm,
                                  'TotalDistance':totalDistanceInKm,
                                  'Status':bikeStatus,
                                  'Time':currentTime,
                                  'Duration':durationString})
        sock.send(json_string)
        WatchDog()
