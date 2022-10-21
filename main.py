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

if __name__ == "__main__":
    main()