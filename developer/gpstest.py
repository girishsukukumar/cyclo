#!/usr/bin/python
import time
import serial
import string
import json
import zmq
import os 
from pynmea import nmea
'''
            ('Timestamp', 'timestamp'),
            ('Latitude', 'latitude'),
            ('Latitude Direction', 'lat_direction'),
            ('Longitude', 'longitude'),
            ('Longitude Direction', 'lon_direction'),
            ('GPS Quality Indicator', 'gps_qual'),
            ('Number of Satellites in use', 'num_sats'),
            ('Horizontal Dilution of Precision', 'horizontal_dil'),
            ('Antenna Alt above sea level (mean)', 'antenna_altitude'),
            ('Units of altitude (meters)', 'altitude_units'),
            ('Geoidal Separation', 'geo_sep'),
            ('Units of Geoidal Separation (meters)', 'geo_sep_units'),
            ('Age of Differential GPS Data (secs)', 'age_gps_data'),
            ('Differential Reference Station ID', 'ref_station_id'))
            #('Checksum', 'checksum'))

$GPRMC
        parse_map = (("Timestamp", "timestamp"),
                     ("Data Validity", "data_validity"),
                     ("Latitude", "lat"),
                     ("Latitude Direction", "lat_dir"),
                     ("Longitude", "lon"),
                     ("Longitude Direction", "lon_dir"),
                     ("Speed Over Ground", "spd_over_grnd"),
                     ("True Course", "true_course"),
                     ("Datestamp", "datestamp"),
                     ("Magnetic Variation", "mag_variation"),
                     ("Magnetic Variation Direction", "mag_var_dir"))
                     #("Checksum", "checksum"))


'''

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def is_integer(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

os.chdir("/home/pi/html/cyclo")
ser = serial.Serial()
ser.port = '/dev/ttyAMA0'
ser.baudrate = 9600
ser.timeout = 1
ser.open()
gpgga = nmea.GPGGA()
gpgsv = nmea.GPGSV()
gpvtg = nmea.GPVTG()
gprmc = nmea.GPRMC()
#print ser
latitude_string = " " 
lat_deg = '0'
lat_mins = '0'
lat_secs = '0.0'
lat_dir  = '0'

lon_deg  = '0'
lon_mins = '0'
lon_secs = '0.0'
long_dir  = '0'
alt      =  '0'
speed_over_ground = '0'
number_of_satellites = '0'
timeStampRaw  = '0'
timeStamp     = '0'
oldTimeStamp  =  0
time_stamp    = '0'
gpsDateParsed = False
gpsTimeParsed = False
gpsTimeSet    =  '0'
GMTOffsetHoursStr = "NOT_SET" 
GMTOffsetMinsStr  = "NOT_SET"

# This is hard coded for India 
# This need to read from a file or read from UI
GMTOffsetHours = 5
GMTOffsetMins  = 30 
 

gps_json =  json.dumps({'LatDeg': '0',
                                   'LatMin': '0',
                                   'LatSec': '0',
                                   'LogDeg': '0',
                                   'LogMin': '0',
                                   'LogSec'   : '0',
                                   'Altitude' : '0',
                                   'LatDir'   : '0',
                                   'LongDir'  : '0',
                                   'Timestamp': '0',
                                   'Speed'    : '0',
                                   'Sat'      : '0',
                                   'GPS_signal_quality' : '0',
                                   'GPS_time_set' : '0'})

number_of_satellites = '0'
speed_over_ground = '0'

# ZeroMQ Context
#gpscontext = zmq.Context()

# Define the socket using the "Context"
#gpssock = gpscontext.socket(zmq.REP)
#gpssock.bind("tcp://127.0.0.1:5681")
lats = "0.0"
longitude = "0.0" 
while True:
    #message = gpssock.recv()
    data = ser.readline()
    #gpssock.send(gps_json) 
    print  data[0:6]
    if data[0:6] == '$GPGGA':
        ##method for parsing the sentence
        gpgga.parse(data)
        gps_quality_indictor = gpgga.gps_qual
        # During field testing it was found that
        # When GPS module looses connection with satellites
        # gps_quality_indictor this will be a empty value
        # As per standards this has to be zero but this GPS 
        # module or the python lib  gpgga.parse has  issue
        # it  does not return zero, instead it
        # returns a empty string or some Alphabet. To fix this 
        # we do a check and if it is found to be non numeric 
        # we set it to ZERO. This happens only when GPS signals are
        # poor
 

        if gps_quality_indictor.isdigit() == False:
           gps_quality_indictor = '0'

        if int(gps_quality_indictor) > 0:
           # We have good signal from GPS
           lats = gpgga.latitude
           #print "Latitude values : " + str(lats)

           lat_dir = gpgga.lat_direction
           #print "Latitude direction : " + str(lat_dir)

           longitude = gpgga.longitude
           #print "Longitude values : " + str(longitude)

           long_dir = gpgga.lon_direction
           #print "Longitude direction : " + str(long_dir)

           time_stamp = gpgga.timestamp
           #print "GPS time stamp : " + str(time_stamp)

           alt = gpgga.antenna_altitude
           #print "Antenna altitude : " + str(alt)

           lat_deg = lats[0:2]
           lat_mins = lats[2:4]
           lat_secs_text = lats[5:]
       
           if lat_secs_text.isdigit() == False :
              lat_secs_text = str(lat_secs)
           lat_secs = round(float(lat_secs_text)*60/10000, 2)


           lon_deg = longitude[0:3]
           lon_mins = longitude[3:5]
           log_secs_text = longitude[6:] 
           #print log_secs_text
           if log_secs_text.isdigit() == False :
              log_secs_text = str(lon_secs) # take the previous value
           lon_secs = round(float(log_secs_text)*60/10000, 2)
        else:
              speed_over_ground = '0'
              number_of_satellites = '0' 
        gps_json = json.dumps({'LatDeg': lat_deg,
                               'LatMin': lat_mins,
                               'LatSec': lat_secs,
                               'LogDeg': lon_deg,
                               'LogMin': lon_mins,
                               'LogSec'   : lon_secs,
                               'Altitude' : str(alt),
                               'LatDir'   :   lat_dir ,
                               'LongDir'  : long_dir,
                               'Timestamp':  time_stamp,
                               'Speed'    : speed_over_ground,
                               'Sat'      : number_of_satellites,
                               'GPS_signal_quality' : gps_quality_indictor,
                               'GPS_time_set' : gpsTimeSet})
       
                                   
                                  
    if data[0:6] == '$GPGSV':
        ##method for parsing the sentence
        gpgsv.parse(data)
        number_of_satellites=  gpgsv.num_sv_in_view 
        if number_of_satellites.isdigit() == False:
           number_of_satellites = 0
       
  
    if data[0:6] == '$GPVTG':
        ##method for parsing the sentence
        gpvtg.parse(data)
        speed_over_ground =  gpvtg.spd_over_grnd_kmph
        if speed_over_ground.isdigit() == False:
           speed_over_ground = 0


    if data[0:6] == '$GPRMC':
        # Method for parsing the sentence
        # Generate a comman string of the format
        # To extract date time
        # sudo date -s "2017-07-18 18:00:00"
        #
        print "GPS: Time signal received"
        if gpsTimeSet == '1':
           continue
           # No need to do parsing as time is already set 
        print "GPS: Processing the time data"
        gprmc.parse(data)
        #print "GPS:" +  gprmc
        timeStampStr = gprmc.timestamp
        print gprmc.timestamp
        print gprmc.datestamp
 
        if is_number(timeStampStr) == True:
           # the following function removes the fractional
           # part from timeStampStr
           print timeStampStr
           timeStampTemp = timeStampStr.split('.',1)
           timeStampRaw = timeStampTemp[0]
           #timeStampRaw,fraction = map(int,timeStampStr.split(".",1))
           print "timeStampRaw: " + timeStampRaw

           #timeStampRaw is hhmmss format we need to change this to
           #hh:mm:ss format

           HourStr   = timeStampRaw[0:2] 
           MinuteStr = timeStampRaw[2:4] 
           SecStr    = timeStampRaw[4:6] 
           # Apply GMT offset to this.
           hours = int(HourStr)
           mins  = int(MinuteStr)

           hours = hours + GMTOffsetHours
           mins  = mins  + GMTOffsetMins

           print "Hours = " + HourStr + "Mins= " + MinuteStr

           hoursBalance = hours / 24
           hours = hours % 24 

           minsBalance = mins/60
           mins  = mins % 60

           hours = hours + minsBalance
           
           # if hoursBalance > 0 :
           # date need to incremented by 1 
           # by taking number of days in a month
           # this is expected to happen only at mid night
           # the best option is to wait for mints and let GPS
           # signal correct by itself.
 
           HourStr = str(hours)
           MinuteStr = str(mins)
           print "Hours = " + HourStr + "Mins= " + MinuteStr
           if hoursBalance == 0 :
              gpsTimeParsed = True
           else:   
              # date need to incremented by 1
              # by taking number of days in a month
              # this is expected to happen only at mid night
              # the best option is to wait for few minutes
              # and let GPS  signal correct by itself.
               
              gpsTimeParsed = False

        else:
           gpsTimeParsed = False 

        # Extract day, month year
        dayStr   =  gprmc.datestamp[0:2]
        monthStr =  gprmc.datestamp[2:4]
        yearStr  =  gprmc.datestamp[4:6]

        if dayStr.isdigit() == True:
            if monthStr.isdigit() == True:
               if yearStr.isdigit() == True:
                  dateStr =  yearStr + '-' + monthStr + '-' +  dayStr
                  gpsDateParsed = True
               else:
                  dateStr = "NOT_SET"
                  gpsDateParsed = False
            else:
               dateStr = 'NOT_SET'
               gpsDateParsed = False
        else:
            dateStr = 'NOT_SET'
            gpsDateParsed = False
        # end nested If then else loop

        if ((gpsDateParsed & gpsTimeParsed) == True):
            # sudo date -s "2017-07-18 18:00:00"
            cmd = 'sudo date -s ' + '"' + dateStr + ' ' 
            cmd = cmd + HourStr + ':'+ MinuteStr + ':' + SecStr + '"'
            print "GPS: " + cmd
            os.system(cmd)
            gpsTimeSet = '1'
        print "gpsTimeSet: " + gpsTimeSet
