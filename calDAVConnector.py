from calendar import calendar
from datetime import datetime, date, time, timezone, timedelta
from time import sleep
from PIL import Image,ImageDraw,ImageFont
import pickle as p
import shutil

import numpy as np
import requests
import sys, os
# sys.path.insert(0, './caldav')
sys.path.insert(0, './e-Paper/RaspberryPi_JetsonNano/python/lib')
# this is now imported via pip
import caldav
from caldav.lib.error import AuthorizationError

#define fonts to be used
eventfont = ImageFont.truetype("./resource/bf_mnemonika_regular.ttf", 16)
weekdayfont = ImageFont.truetype("./resource/bf_mnemonika_regular.ttf", 16)
timefont = ImageFont.truetype("./resource/bf_mnemonika_regular.ttf", 12)
birthdayfont = weekdayfont


def main():
    t1 = datetime.now()
    config_dict = read_config("../myconfig")
    print("read config")
    
    while(True):
        t2 = datetime.now()
        shutil.copyfile(config_dict["datafile"],config_dict["datafile_old"])
        server_reached = test_cal_server_connection(config_dict["caldav_url"], config_dict["username"], config_dict["password"])
        if server_reached:
            client = make_client(config_dict["caldav_url"], config_dict["username"], config_dict["password"])
            if client:
                client_established = True
                birthdays, time_events, day_events = get_calendar_data(client, config_dict["selected_cals"], config_dict["birthdaycal"])
                dump_cal_data(config_dict["datafile"], day_events, time_events, birthdays)
            else:
                client_established = False
        else:
            birthdays, time_events, day_events = load_cal_data(config_dict["datafile"])
        #with this information now the week calendar can be painted on a 800x480 bitmap.
        # if new data changed or draw_now is on, display new data
        #if (config_dict["draw_now"] or not client_established or not cal_data_issame(config_dict["datafile"], config_dict["datafile_old"]) or not os.path.exists("canvas.bmp")):
        print("need to redraw the calendar...")
        if not config_dict["colormode"]:
            Himage = draw_calendar(birthdays, time_events, day_events, config_dict["language"],
            config_dict["weekday_format"], config_dict["draw_date"],
            config_dict["colormode"], config_dict["draw_now"], position = [0.5,0], scale = [0.5,0.5])
            Himage = draw_warnings(Himage, server_reached, client_established)
            Himage.save("./canvas.bmp")
        else:
            Himage, HRimage = draw_calendar(birthdays, time_events, day_events, config_dict["language"],
            config_dict["weekday_format"], config_dict["draw_date"],
            config_dict["colormode"], config_dict["draw_now"], position = [0.5,0], scale = [0.5,0.5])
            Himage = draw_warnings(Himage, server_reached, client_established)
            Himage.save("./canvas.bmp")
            HRimage.save("./r_canvas.bmp")

        if(config_dict["on_e_paper"]):
            #load epd library
            from waveshare_epd import epd7in5b_V2
            #initialise epd for the e-ink display
            epd = epd7in5b_V2.EPD()
            epd.init()
            epd.Clear()
            if config_dict["colormode"]:
                epd.display(epd.getbuffer(Himage), epd.getbuffer(HRimage))
            else:
                epd.display(epd.getbuffer(Himage))
        #else:
        #    print("no need to redo anything...")
        t4 = datetime.now()
        delta = t4-t2
        print('needed', delta)
        sleeptime = float(config_dict["update_time"])-delta.total_seconds() if float(config_dict["update_time"])-delta.total_seconds()>0 else 0
        print("sleeping for", sleeptime, "s" )
        sleep(sleeptime)
    return

def read_config(conf_file):
    conflib = {}
    # defaults
    conflib["caldav_url"] = ''
    conflib["username"] = ''
    conflib["password"] = ''
    conflib["datafile"] = ''
    conflib["selected_cals"] = []
    conflib["birthdaycal"] = ''
    conflib["language"]="EN"
    conflib["weekday_format"] = "FULL"
    conflib["draw_date"] = False
    conflib["colormode"] = False
    conflib["on_e_paper"] = False
    conflib["draw_now"] = False
    conflib["update_time"] = 600
    #open config file, load configs

    if (os.path.isfile(conf_file)):
        configfile = open(conf_file, "r")
        conf = configfile.readlines()
        #print(conf)
        for l in conf:
            l = l.strip()
            if not l.startswith("#"):
                key = l.split(" ")[0]
                if key in ["draw_date", "colormode", "on_e_paper", "draw_now"]:
                    #inperpret some values as bool
                    value = False
                    if l.split(" ")[1] == "True":
                        value = True
                elif key in ["selected_cals","birthdaycal"]:
                    # interpret some values as list
                    value = l.split(" ")[1]
                    for s in l.split(" ")[2:]:
                        value += " "+s
                    value = value.split(";")
                else:
                    value = l.split(" ")[1]
                conflib[key] = value
    # else mv config ot upper directory
    return conflib

def test_cal_server_connection(caldav_url, username, password):
    #look if server and user are set
    if(len(caldav_url) == 0):
        print("Please provide a calDAV link")
    if(len(username) == 0):
        print("Please provide a username")

    #calDAV setup

    timeout = 5

    server_reached = True

    print("Looking for server...")
    try:
        request = requests.get(caldav_url, timeout=timeout)
    except (requests.ConnectionError, requests.Timeout) as exception:
        print("didn't find server, showing data from last successful connection")
        server_reached = False
    else:
        print("found server")
    return server_reached

def make_client(caldav_url, username, password):
    try:
        client = caldav.DAVClient(url=caldav_url, username=username, password=password)
    except (Exception) as ex:
        client = None
        #if server is available, download new information from server
    return client

def get_calendar_data(client, selected_cals, birthdaycal):
    #check in which time zone we are
    tz = timedelta(minutes = round((datetime.now()-datetime.utcnow()).seconds/60))

    print("Successfully connected to server, downloading calendars...")
    my_principal = client.principal()
    calendars_fetched = my_principal.calendars()
    calendars = []
    if not (len(selected_cals) == 0 or len(selected_cals[0]) == 0):
        for c in calendars_fetched:
            if c.name in selected_cals:
                calendars.append(c)
    else:
        calendars = calendars_fetched
    print("selected calendars:")
    for c in calendars:
        print(c.name)
    
    time_events = []
    day_events = []
    birthdays = []
    #go through all calendars to look for events
    for c in calendars:
        # print(c)
        current_calendar = my_principal.calendar(name=c.name)
        events_fetched = current_calendar.date_search(
        start=datetime.today()-timedelta(days = datetime.today().weekday()), end=datetime.today()+timedelta(days = 6-datetime.today().weekday()), expand=True)
        if len(events_fetched)> 0:
            for event in events_fetched:
                event_start_str = str(event.vobject_instance.vevent.dtstart)[10:-1]
                event_end_str = str(event.vobject_instance.vevent.dtend)[8:-1]
                #print(event_start_str)
                
                if(event_start_str.startswith("VALUE")):
                    #if it is an event over a whole day, sort it into the day events
                    if(c.name in birthdaycal):
                        summary = str(event.vobject_instance.vevent.summary.value)
                        pieces = summary.split(" ")
                        age = date.today().year - int(pieces[2][2:-1])
                        birthdays.append({
                            "START":date(int(event_start_str.split("}")[1].split("-")[0]),int(event_start_str.split("}")[1].split("-")[1]),int(event_start_str.split("}")[1].split("-")[2])),
                            "END":date(int(event_end_str.split("}")[1].split("-")[0]),int(event_end_str.split("}")[1].split("-")[1]),int(event_end_str.split("}")[1].split("-")[2])),
                            "SUMMARY":pieces[1]+" "+pieces[0][:-1]+" ("+str(age)+")", 
                            "CALENDAR":c.name
                            })
                    else:
                        day_events.append({
                            "START":date(int(event_start_str.split("}")[1].split("-")[0]),int(event_start_str.split("}")[1].split("-")[1]),int(event_start_str.split("}")[1].split("-")[2])),
                            "END":date(int(event_end_str.split("}")[1].split("-")[0]),int(event_end_str.split("}")[1].split("-")[1]),int(event_end_str.split("}")[1].split("-")[2])),
                            "SUMMARY":str(event.vobject_instance.vevent.summary.value), 
                            "CALENDAR":c.name
                            })
                else:
                    #otherwise it has to be a time event
                    sd = event_start_str.split(" ")[0]
                    st = event_start_str.split(" ")[1]
                    sh = int(st.split(":")[0])+int(st.split(":")[2][2:4])
                    sm = int(st.split(":")[1])+int(st.split(":")[3])
                    ss = int(st.split(":")[2][0:1])
                    ed = event_end_str.split(" ")[0]
                    et = event_end_str.split(" ")[1]
                    eh = int(et.split(":")[0])+int(st.split(":")[2][2:4])
                    em = int(et.split(":")[1])+int(et.split(":")[3])
                    es = int(et.split(":")[2][0:1])
                    time_events.append({
                        "START":datetime(int(sd.split("-")[0]),int(sd.split("-")[1]),int(sd.split("-")[2]), hour = sh, minute = sm, second = ss)+tz,
                        "END":datetime(int(ed.split("-")[0]),int(ed.split("-")[1]),int(ed.split("-")[2]), hour = eh, minute = em, second = es)+tz,
                        "SUMMARY":str(event.vobject_instance.vevent.summary.value), 
                        "CALENDAR":c.name
                        })
    #if the user wants one calendar to be treated as a birthday calendar, these are sorted into an extra library
    print("Download complete")
    return birthdays, time_events, day_events

def dump_cal_data(datafile, day_events, time_events, birthdays):
    #back up the data received to a local copy so that it can be displayed if needed
    if(len(datafile)!= 0):
        calendarlib = {"DAY_EVENTS":day_events,"TIME_EVENTS":time_events,"BIRTHDAYS":birthdays}
        p.dump( calendarlib, open(datafile, "wb"))
    return

def load_cal_data(datafile):
    #if the server is not available, instead load information from datafile
    if(len(datafile)!= 0):
        print("Loading caldata...")
        calendarlib = p.load(open(datafile,"rb"))
        time_events = calendarlib["TIME_EVENTS"]
        day_events = calendarlib["DAY_EVENTS"]
        birthdays = calendarlib["BIRTHDAYS"]
        return birthdays, time_events, day_events
    else:
        print("No data available!")
        exit()

def cal_data_issame(file_old, file_new):
    birthdays_old, time_events_old, day_events_old = load_cal_data(file_old)
    birthdays_new, time_events_new, day_events_new = load_cal_data(file_new)
    events_old = [birthdays_old, time_events_old, day_events_old]
    events_new = [birthdays_new, time_events_new, day_events_new]
    # compare birthdays
    for i in range(3):
        if len(events_new[i]) == len(events_old[i]):
            for event in events_new[i]:
                found_pair = False
                for event2 in events_old[i]:
                    if event["SUMMARY"] == event2["SUMMARY"] and event["START"] == event2["START"] and event["END"] == event2["END"] and event["CALENDAR"] == event2["CALENDAR"]:
                        #print("found a pair")
                        found_pair = True
                if not found_pair:
                    return False
        else:
            return False
    return True

#define function to insert text at a 90 degree angle
def draw_text_90_into (text: str, into, at):
    # Measure the text area
    wi, hi = eventfont.getsize(text)

    # Copy the relevant area from the source image
    img = into.crop ((at[0], at[1], at[0] + hi, at[1] + wi))

    # Rotate it backwards
    img = img.rotate (90, expand = 1)

    # Print into the rotated area
    d = ImageDraw.Draw (img)
    d.text ((0, 0), text, font = eventfont, fill = 0)

    # Rotate it forward again
    img = img.rotate (270, expand = 1)

    # Insert it back into the source image
    # Note that we don't need a mask
    into.paste (img, at)

#only for testing purposes

def draw_calendar(birthdays, time_events, day_events, language, weekday_format, draw_date, has_color, draw_now, **kwargs):
    #create image buffer
    if "scale" in kwargs:
        scale = kwargs.get("scale")
        width = round(scale[0]*800)
        height = round(scale[1]*480)
    else:
        width = 800
        height = 480
    if "position" in kwargs:
        position = kwargs.get("position")
        position_px = [round(position[0]*800),round(position[1]*480)]
    else:
        position_px = [0,0]
    Himage = Image.new('1', (width,height), 255)  # 255: clear the frame
    draw = ImageDraw.Draw(Himage)
    if(has_color):
        HRimage = Image.new('1', (width,height), 255)  # 255: clear the frame
        draw_r = ImageDraw.Draw(HRimage)

    #define language, and if abbreviations for weekdays should be used

    #define grid coordinates
    upper_border_grid = position_px[1]
    lower_border_grid = position_px[1]+height-15
    left_border_grid = position_px[0] + 15
    right_border_grid = position_px[0] + width - 15
    first_hour = kwargs.get("first_hour") if ("first_hour" in kwargs) else 6
    last_hour = kwargs.get("last_hour") if ("last_hour" in kwargs) else 23

    #calculate some grid related stuff
    hours_in_day = last_hour-first_hour
    width_grid = right_border_grid-left_border_grid
    width_day = round(width_grid/7)
    height_grid = lower_border_grid-upper_border_grid
    weekday_height = weekdayfont.getsize("Monday")[1]
    if(birthdays == []):
        upper_border_writable = upper_border_grid+weekday_height
    else:
        birthday_height = birthdayfont.getsize("ABCDEFGHIJKLMNOPQRSTUVWXYZÄÜÖabcdefghijklmnpqrstuvwxyzäüö")[1]
        upper_border_writable = upper_border_grid+weekday_height+birthday_height+3
    two_hour_space = round(2*(lower_border_grid-(upper_border_grid+weekday_height+2))/hours_in_day)
    last_hour_line = round((hours_in_day-(hours_in_day%2))*two_hour_space/2+upper_border_grid+weekday_height+2)
    #write down weekdays, makes next step easier
    weekdays = {
                "EN":{
                    "FULL":["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],
                    "SHORT":["Mo","Tu","We","Th","Fr","Sa","Su"]
                    },
                "GER":{
                    "FULL":["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"],
                    "SHORT":["Mo","Di","Mi","Do","Fr","Sa","So"]
                    },
                "FRE":{
                    "FULL":["Lundi", "Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"],
                    "SHORT":["Lu", "Ma","Me","Je","Ve","Sa","Di"]
                    }
                }

    #draw the weekdays
    monday = datetime.today()-timedelta(days = datetime.today().weekday())
    free_days = [5,6]

    for j in range(len(weekdays[language][weekday_format])):
        if draw_date:
            if(max([(weekdayfont.getsize(i+", "+str((monday+timedelta(days=j)).day)+"."+str((monday+timedelta(days=j)).month)+".")[0]>width_day-7) for i in weekdays[language]["FULL"]])):
                weekday_format = "SHORT"
            w_str = (weekdays[language][weekday_format][j]+", "+str((monday+timedelta(days=j)).day)+"."+str((monday+timedelta(days=j)).month)+".")    
        else:
            if(max([(weekdayfont.getsize(i)[0]>width_day-7) for i in weekdays[language]["FULL"]])):
                weekday_format = "SHORT"
            w_str = (weekdays[language][weekday_format][j])
        if has_color and j in free_days:
            draw_r.text((left_border_grid+j*width_day+5, upper_border_grid),w_str, font = weekdayfont, fill = 0)
        else:
            draw.text((left_border_grid+j*width_day+5, upper_border_grid),w_str, font = weekdayfont, fill = 0)

    # draw birthdays
    for event in birthdays:
        cropped_ev_str = (event["SUMMARY"])
        if (birthdayfont.getsize(cropped_ev_str)[0] > width_day-4):
            p_list = cropped_ev_str.split(" ")
            p_list[-2] = p_list[-2][0]+"."
            cropped_ev_str = ""
            for l in p_list:
                cropped_ev_str += l+" "
            print(cropped_ev_str)
            while (birthdayfont.getsize(cropped_ev_str)[0] > width_day-4):
                cropped_ev_str = cropped_ev_str.split("(")[0][:-1]+"("+cropped_ev_str.split("(")[1]
        d = event["START"].weekday()
        if has_color:
            draw_r.text((left_border_grid+d*width_day+5, upper_border_grid+weekday_height+2),cropped_ev_str, font = weekdayfont, fill = 0)
        else:
            draw.text((left_border_grid+d*width_day+5, upper_border_grid+weekday_height+2),cropped_ev_str, font = weekdayfont, fill = 0)

    #draw a grid
    draw.line([(left_border_grid, upper_border_writable+2),(right_border_grid, upper_border_writable+2)], fill=0, width=2)
    for y in range(width_day,width_grid,width_day):
        draw.line([(y+left_border_grid, upper_border_grid),(y+left_border_grid, lower_border_grid)], fill=0, width=2)

    for y in range(upper_border_writable+2,lower_border_grid,two_hour_space):
        for x in range(left_border_grid, right_border_grid, 6):
            draw.line([(x, y), (x+2, y)], fill = 0, width = 1)

    #draw times for orientation
    i = 0
    for y in range(upper_border_writable+4,lower_border_grid,two_hour_space):
        draw.text((left_border_grid-timefont.getsize(str(i*2+first_hour))[0], y), str(i*2+first_hour), font = timefont, fill = 0)
        i +=1

    already_an_event = np.zeros((7,lower_border_grid - upper_border_grid))

    known_calendars = {"DLRG Kalendar" : "DLRG", "Uni Kalendar" : "UNI", "Persönlich" : "PER"}

    for event in day_events:
        for d in range(event["START"].weekday(),(event["END"].weekday()) if(event["END"]<(monday+timedelta(days=6)).date()) else 7):
            print(d)
            row = width_day*d+left_border_grid+4
            if event["CALENDAR"] in known_calendars:
                cal = known_calendars[event["CALENDAR"]]
            else:
                cal = event["CALENDAR"]
            if(np.amax(already_an_event[d,:])== 0):
                draw.rectangle((row,upper_border_writable+5,row+width_day-6,lower_border_grid-1),fill = 255)
                draw.line([(row,upper_border_writable+5),(row,lower_border_grid-1)], width = 4, fill = 0)
                draw.line([(row,lower_border_grid-2),(row+width_day-6,lower_border_grid-2)], width = 2, fill = 0)
                draw.line([(row,upper_border_writable+5),(row+width_day-6,upper_border_writable+5)], width = 2, fill = 0)
                draw.line([(row+width_day-7,upper_border_writable+5),(row+width_day-7,lower_border_grid-1)], width = 2, fill = 0)
                wi, hi = eventfont.getsize (event["SUMMARY"])
                draw_text_90_into("["+cal+"] "+event["SUMMARY"], Himage, (row+4,round(height_grid/2-(weekday_height+5)-wi/2)))
            else:
                wi, hi = eventfont.getsize(event["SUMMARY"])
                draw.line([(row+6+hi,upper_border_writable+9),(row+6+hi,lower_border_grid-4)], width = 2, fill = 0)
                draw_text_90_into("["+cal+"] "+event["SUMMARY"], Himage, (row+10+hi,round(height_grid/2-(weekday_height+5)-wi/2)))    
            already_an_event[d,:] += 1

    for event in time_events:
        #draw rectangle
        #find the place via day and time to coordinate conversion
        
        row_start = width_day*event["START"].weekday()+left_border_grid+4
        row_end = width_day*event["END"].weekday()+left_border_grid+4
        right_border_event = row_start+width_day-6
        upper_border_event = round(upper_border_writable+5+((lower_border_grid-(upper_border_writable+5))/hours_in_day)*(event["START"].hour-first_hour+(event["START"].minute/60)))
        lower_border_event = round(upper_border_writable+5+((lower_border_grid-(upper_border_writable+5))/hours_in_day)*(event["END"].hour-first_hour+(event["END"].minute/60)))
        left_border_event = row_start+((np.amax(already_an_event[event["START"].weekday(),upper_border_event:lower_border_event]))*6)
        already_an_event[event["START"].weekday(),upper_border_event:lower_border_event] +=1
        if (row_start == row_end): 
            draw.rectangle((left_border_event,upper_border_event,right_border_event,lower_border_event),fill = 255)
            if(lower_border_event<lower_border_grid):
                draw.line([(left_border_event,lower_border_event),(right_border_event,lower_border_event)], width = 2, fill = 0)
            draw.line([(left_border_event,upper_border_event),(left_border_event, min(lower_border_event,lower_border_grid))], width = 4, fill = 0)
            draw.line([(right_border_event-1,upper_border_event),(right_border_event-1,min(lower_border_event,lower_border_grid))], width = 2, fill = 0)
            draw.line([(left_border_event,upper_border_event),(right_border_event,upper_border_event)], width = 2, fill = 0)
        else:
            draw.rectangle((left_border_event,upper_border_event,right_border_event,lower_border_grid),fill = 255)
            draw.line([(left_border_event,upper_border_event),(left_border_event,lower_border_grid-1)], width = 4, fill = 0)
            draw.line([(right_border_event-1,upper_border_event),(right_border_event-1,lower_border_grid-2)], width = 2, fill = 0)
            draw.line([(left_border_event,upper_border_event),(right_border_event,upper_border_event)], width = 2, fill = 0)
            for d in range(event["START"].weekday()+1,event["END"].weekday()):
                draw.rectangle((left_border_event+(d*width_day),upper_border_writable+5,right_border_event+(d*width_day),lower_border_grid),fill = 255)
                draw.line([(left_border_event+(d*width_day),upper_border_writable+5),(left_border_event+(d*width_day),lower_border_grid-1)], width = 4, fill = 0)
                draw.line([(right_border_event-1+(d*width_day),upper_border_writable+5),(right_border_event-1+(d*width_day),lower_border_grid-2)], width = 2, fill = 0)
            if(event["END"].hour> first_hour):
                draw.rectangle((left_border_event+((event["END"].weekday()-event["START"].weekday())*width_day),upper_border_writable+5,right_border_event+((event["END"].weekday()-event["START"].weekday())*width_day),lower_border_event),fill = 255)
                draw.line([(left_border_event+((event["END"].weekday()-event["START"].weekday())*width_day),upper_border_writable+5),(left_border_event+((event["END"].weekday()-event["START"].weekday())*width_day),lower_border_event)], width = 4, fill = 0)
                draw.line([(right_border_event-1+((event["END"].weekday()-event["START"].weekday())*width_day),upper_border_writable+5),(right_border_event-1+((event["END"].weekday()-event["START"].weekday())*width_day),lower_border_event)], width = 2, fill = 0)
            if(lower_border_event<lower_border_grid):
                draw.line([(left_border_event+((event["END"].weekday()-event["START"].weekday())*width_day),lower_border_event),(right_border_event+((event["END"].weekday()-event["START"].weekday())*width_day),lower_border_event)], width = 2, fill = 0)
        
        #use abbreviations for some calendars...
        if event["CALENDAR"] in known_calendars:
            cal = known_calendars[event["CALENDAR"]]
        else:
            cal = event["CALENDAR"]
        wi,hi = eventfont.getsize(event["SUMMARY"])
        #format event title, calendar and time to fit into the rectangle
        if(event["START"].day == event["END"].day and lower_border_event-upper_border_event-2 < hi) or lower_border_grid-upper_border_event-2 < hi:
            cropped_ev_str = ('{:2d}'.format(event["START"].hour)+":"+'{:02d}'.format(event["START"].minute)+ " " +event["SUMMARY"])
            while (eventfont.getsize(cropped_ev_str)[0] > right_border_event-left_border_event-4):
                cropped_ev_str = cropped_ev_str[:-1]
            draw.text((left_border_event+6, lower_border_event+4),cropped_ev_str, font = eventfont, fill = 0)
        
        elif(event["START"].day == event["END"].day and lower_border_event-upper_border_event-2 < hi*2) or lower_border_grid-upper_border_event-2 < hi*2:
            cropped_ev_str = ('{:2d}'.format(event["START"].hour)+":"+'{:02d}'.format(event["START"].minute)+ " " +event["SUMMARY"])
            while (eventfont.getsize(cropped_ev_str)[0] > right_border_event-left_border_event-4):
                cropped_ev_str = cropped_ev_str[:-1]
            draw.text((left_border_event+6, upper_border_event+4),cropped_ev_str, font = eventfont, fill = 0)   
        
        else:
            cropped_ev_str = (event["SUMMARY"])
            while (eventfont.getsize(cropped_ev_str)[0] > right_border_event-left_border_event-4):
                cropped_ev_str = cropped_ev_str[:-1]
            draw.text((left_border_event+6, upper_border_event+4+eventfont.getsize(cropped_ev_str)[1]),cropped_ev_str, font = eventfont, fill = 0)

            cropped_ev_str = (('{:2d}'.format(event["START"].hour)+":"+'{:02d}'.format(event["START"].minute)+" ["+cal+"]"))
            while (eventfont.getsize(cropped_ev_str)[0] > right_border_event-left_border_event-4):
                cropped_ev_str = cropped_ev_str[:-1]
            draw.text((left_border_event+6, upper_border_event+4),cropped_ev_str, font = eventfont, fill = 0)

    # draw a line for current date and time
    if draw_now:
        now_row = width_day*datetime.now().weekday()+left_border_grid
        now_time = round(upper_border_writable+5+(((last_hour_line-(upper_border_writable+5))/(hours_in_day-(hours_in_day%2)))*(datetime.now().hour-first_hour+(datetime.now().minute/60))))
        if(now_time < lower_border_grid and now_time > upper_border_writable+2):
            if has_color:
                draw_r.line([(now_row,now_time),(now_row+width_day-2,now_time)], width = 2, fill = 0)
                draw_r.ellipse((now_row, now_time, now_row+10, now_time+4), fill = 0)
            else:
                draw.line([(now_row,now_time),(now_row+width_day-2,now_time)], width = 2, fill = 0)
                draw.ellipse((now_row, now_time, now_row+10, now_time+4), fill = 0)
        
    if not has_color:
        return Himage
    else:
        return Himage, HRimage

def draw_warnings(Himage, server_reached, client_established):
    #draw warnings, if something went wrong with the connection
    if(not server_reached):
        Himage.paste(Image.open("./resource/server_unreachable.png"), (right_border_grid-40,lower_border_grid-40))
    if(not client_established):
        Himage.paste(Image.open("./resource/unauthorized.png"), (right_border_grid-40,lower_border_grid-40))
    return Himage
    
if __name__ == "__main__":
    main()