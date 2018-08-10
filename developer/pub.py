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
pedalingDuration = 0       #  How long the cycle was moving or pedaling 
pedalingDurationInHours = 0
tripDuration = 0           # pedalingDuration + duration of rest period 
averageSpeed = 0
localtime      =   time.localtime(time.time()) # Current Local Time 
tripStartTime  =   int(time.time()) 
data_saved_time  = 0
no_of_satellites = '0' 
gps_time_set     = '0'
old_gps_time_set = '0' # We need this flag to reset all globals the moment GPS has set the clock.
restDuration = 0

# Global for calculating speed  and Cadence RPM
# Circumference 2.23 meters
# @ 40 km hour  6.22 rotation per sec
# @ 20 km hour  3.11 rotation per sec
# @ 10 km hour  1.5 rotation per sec

speed_pulse         = 0 
cadence_pulse       = 0
TIME_DELTA_SPEED    = 2
CIRCUMFERENCE       = 2.23 
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

logging.basicConfig(filename='cyclepub.log', level=logging.INFO)
logging.info('Cycle Pub Started')

#log = logging.getLogger('werkzeug')
#log.setLevel(logging.INFO)

# GPIO 23 and 24 set up as an input, pulled down, connected to 3V3 on button press
# now we'll define two IST  functions
# these will run in another thread when our events are detected


def SaveDataSet(lat_deg,lat_min,lat_sec,lat_dir,
                log_deg, log_min,log_sec,
                log_dir,alt,gps_quality):

    global CurrentCadence
    global speedInKmPerHr
    global localtime
    global tripStartTime 

    today     = datetime.date.today()
    hr        = localtime.tm_hour
    min       = localtime.tm_min
    sec       = localtime.tm_sec

    fileName = str(today) 
    latitude = str(lat_deg)  + " " + str(lat_min) + " " + str(lat_sec) + " " + str(lat_dir)
    longitude = str(log_deg) + " " + str(log_min) + " " + str(log_sec) + " " + str(log_dir)

    record = open(fileName,'a') # File opened
    # format the time, Cadence and Speed into string 
    recordString = fileName + " ; "
    recordString = recordString + str(hr) +  '_' + str(min) +  '_' + str(sec) + " ; " 
    recordString = recordString + str(CurrentCadence) + ' ; ' 
    recordString = recordString + str(speedInKmPerHr) + " ; " 
    recordString = recordString + str(latitude) + ' ; ' 
    recordString = recordString + str(longitude) + ' ; ' 
    recordString = recordString + str(alt) + " " +  " ; "
    recordString = recordString + str(gps_quality) + " "
    recordSrting = recordString + " " + "\n" 

    record.write(recordString) # Data Written
    record.write("\n")
    record.close()             # File Closed

    printLog = "Data set saved at : " +str(hr)+":"+str(min)+":"+str(sec)
    logging.info(printLog)

    return


def WatchDog(signum,frame):
    global bikeStatus
    global lastTimePulseReceived
    timeNow = int(time.time())
    diff = timeNow - lastTimePulseReceived
    if diff  > SENSOR_IDLE_TIME : # if cycle is stopped for more than 5 sec
        CurrentCadence = 0  # show that cadence is zero
        CurrentSpeed   = 0  # show that speed is zero
        bikeStatus = "Stopped"

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
    global pedalingDuration 
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
       pedalingDuration = pedalingDuration + timeDelta
       

def Cadence_Sensor_ISR(channel):
    global cadence_pulse
    global cadence_calc_start_time
    global CurrentCadence
    cadence_pulse = cadence_pulse + 1
    timeNow = int(time.time())
    timeDelta = timeNow - cadence_calc_start_time
    if timeDelta  > TIME_DELTA_CADENCE:
       CurrentCadence = cadence_pulse * 6 # for 60 specs 
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

gps_context = zmq.Context()
sock_to_gps = gps_context.socket(zmq.REQ)
sock_to_gps.connect("tcp://127.0.0.1:5681")


# *********************************
# Create a watch dog timer for 5 sec to monitor 
# whether cycle is running or not
# if not running reset all parameters to ZERO
# WatchDog is the name of the call back function 
# that will be executed 
# *********************************
signal.signal(signal.SIGALRM,WatchDog)
init = time.time()
signal.setitimer(signal.ITIMER_REAL,5,6)
# end of watch dog

## sock.RCVTIMEO  = 3000 Did not behave as expected
# instead program crashed need more investigation

while True:

    message = sock.recv()
    printLog = "Message Recvd" + message
    logging.info(printLog)
    if message == "ResetTrip":
       logging.info('ResetTrip')
       CurrentSpeed = 0
       CurrentCadence = 0
       cadence_calc_start_time =  int(time.time()) 
       speed_calc_start_time =  int(time.time()) 
       trip_distance = 0
       speedInKmPerHr = 0
       distanceInKm   = 0
       bikeStatus = "Stopped"
       pedalingDuration = 0
       tripStartTime =  int(time.time()) 
       tripDuration  = 0
       data_saved_time = 0
       restDuration = 0
       json_string = json.dumps({'Speed': speedInKmPerHr,
                                  'Cadence': CurrentCadence,
                                  'Distance': distanceInKm,
                                  'TotalDistance':totalDistanceInKm,
                                  'Status':bikeStatus,
                                  'Time':currentTime,
                                  'Duration':tripDuration,
                                  'Satellites' : no_of_satellites ,
                                  'GPSTimeSet': gps_time_set_flag,
                                  'AverageSpeed': averageSpeed,
                                  'RestDuration' : restDuration})
       sock.send(json_string)

    elif message == "Shutdown":
       bikeStatus = "Shutdown"
       json_string = json.dumps({'Speed': speedInKmPerHr,
                                  'Cadence': CurrentCadence,
                                  'Distance': distanceInKm,
                                  'TotalDistance':totalDistanceInKm,
                                  'Status':bikeStatus,
                                  'Time':currentTime,
                                  'Duration':tripDuration,
                                  'Satellites' : no_of_satellites, 
                                  'AverageSpeed': averageSpeed,
                                  'GPSTimeSet': gps_time_set_flag,
                                  'RestDuration' : restDuration})

       # perform shutdown
       # save all data
       sock.send(json_string)
       os.system('sudo shutdown now') 
    else:
        # get GPS data
        sock_to_gps.send("hello")
        gps_json_data = sock_to_gps.recv()
        parsed_gps_json = json.loads(gps_json_data) 

        no_of_satellites = parsed_gps_json['Sat'] 
        lat_degree = parsed_gps_json['LatDeg']
        lat_min = parsed_gps_json['LatMin']
        lat_sec = parsed_gps_json['LatSec']
        
        lat_dir = parsed_gps_json['LatDir']

        log_degree = parsed_gps_json['LogDeg']
        log_min    = parsed_gps_json['LogMin']
        log_sec    = parsed_gps_json['LogSec']
        log_dir    = parsed_gps_json['LongDir']
        gps_quality_indicator = parsed_gps_json['GPS_signal_quality']
        gps_time_set = parsed_gps_json['GPS_time_set'] 
        altitude = parsed_gps_json['Altitude']

        # Break down  current time  into hours:Minutes:Seconds
        # then format into a string
        localtime = time.localtime(time.time()) 
        hr = localtime.tm_hour
        min = localtime.tm_min
        sec = localtime.tm_sec
        currentTime = str(hr) + ":" + str(min) + ":" + str(sec) 
        printLog = "Current Time Str = " + currentTime 
        logging.info(printLog)

        currentTimeInSec = (int(time.time())) 

        printLog = "Current Time in Sec= " +  str(currentTimeInSec)
        logging.info(printLog)

        printLog = "tripStartTime = " +  str(tripStartTime)
        logging.info(printLog)


        tripDuration =  currentTimeInSec - tripStartTime

        printLog = "tripDuration = " +  str(tripDuration)
        logging.info(printLog)

        # End of breaking down current time and making into to a string
   
        # Convert Speed which is in meters per to km/hour 
        speedInKmPerHr = round((CurrentSpeed * 3.6),1)

        # Distance is in meters convert it into km 
        distanceInKm   = round(trip_distance/1000,1)
        totalDistanceInKm = round(totalDistance/1000,1)

        # Calculate Average Speed
        # if the cycling has pedaled for more than 10 minutes ie is 600 secs

        printLog = "Pedaling Duration = " + str(pedalingDuration)
        logging.info(printLog)
        if pedalingDuration > 600: 
           pedalingDurationInHours = float(float(pedalingDuration)/float(3600))
        if pedalingDurationInHours > 0:
          averageSpeed = round((distanceInKm/pedalingDurationInHours),1) 
        else:
          averageSpeed = 0.0
        # End of AVerage speed calculation

        # *****Save the data set every 60 secs for upload to cloud
        printLog = "GPS Time state before logging = " + gps_time_set
        logging.info(printLog)

        if (gps_time_set == '1'): 
           # Only after GPS signals are reliable and time is set we
           # intend to record the trip data. Till then data is only for
           # display purpose

           printLog = "tripDuration = " + str(tripDuration)
           logging.info(printLog)
           
           printLog = "data_saved_time = " + str(data_saved_time)
           logging.info(printLog)

           printLog = "Date Save period = " + str(tripDuration-data_saved_time)
           logging.info(printLog)

           if (tripDuration - data_saved_time) > DATA_SET_SAVE_PERIOD:
              SaveDataSet(lat_degree, lat_min,lat_sec,lat_dir,
                          log_degree,log_min,log_sec,
                          log_dir,altitude,
                          gps_quality_indicator)

              data_saved_time = tripDuration
        # ******End of Save the data set

        # ****************************************************
        # tripDuration is in Seconds
        # Break downs tripDuration into hours:Minutes:Seconds
        # Procedure:
        # Trip duration mod 60 will give secs 
        # quotient of tripDuration / 60 will give time in mins 
        # timeinminutes mod 60 will give minutes
        # quotient of time in minutes / 60 will give hours
        # *************************************************
        seconds = tripDuration % 60 # modulus operation
        balanceTimeInMinutes = tripDuration / 60 # Quotient
        minutes = balanceTimeInMinutes % 60 # modulus operation 
        hours = balanceTimeInMinutes /60 #Quotient 
            
        # variables hours, minites and seconds are formatted into a string

        durationString  = str(hours) + ":" + str(minutes) + ":" + str(seconds)  

        # End of breaking down tripDuration and making into to a string
        # ****************************************************

        restingTime = tripDuration - pedalingDuration
        restingTimeStr = str(restingTime)

        if gps_time_set == '1':
           gps_time_set_flag = 'Yes' 
           if old_gps_time_set == '0':
              # This is the moment GPS has set the time
              # We need to reset globals which are set during start up

              printLog = "GPS Time set and all globals reset to start"
              logging.info(printLog)
              old_gps_time_set = '1'
              pedalingDuration =0
              currentTimeInSec = (int(time.time()))
              tripDuration = 0
              data_saved_time = 0
              averageSpeed = 0
              localtime      =   time.localtime(time.time()) # Current Local Time
              tripStartTime  =   int(time.time()) 
              restDuration = 0
 
        else:
           gps_time_set_flag = 'No' 

        json_string = json.dumps({'Speed': speedInKmPerHr,
                                  'Cadence': CurrentCadence,
                                  'Distance': distanceInKm,
                                  'TotalDistance':totalDistanceInKm,
                                  'Status':bikeStatus,
                                  'Time':currentTime,
                                  'Duration':durationString,
                                  'Satellites' : no_of_satellites, 
                                  'AverageSpeed': averageSpeed, 
                                  'GPSTimeSet': gps_time_set_flag,
                                  'RestDuration' : restDuration})
        sock.send(json_string)
