from datetime import datetime
from datetime import date
from datetime import timedelta
from PIL import Image,ImageDraw,ImageFont
import pickle as p

import requests
import sys
import getopt
sys.path.insert(0, './caldav')
import caldav
from caldav.lib.error import AuthorizationError

#look for commandline args

import getopt


inputfile = ''
outputfile = ''
try:
    opts, args = getopt.getopt(sys.argv[1:],"h:i:o",["ifile=","ofile="])
except getopt.GetoptError:
    print('test.py -i <inputfile> -o <outputfile>')
    sys.exit(2)
for opt, arg in opts:
    if opt == '-h':
        print ('test.py -i <inputfile> -o <outputfile>')
        sys.exit()
    elif opt in ("-i", "--ifile"):
        inputfile = arg
    elif opt in ("-o", "--ofile"):
        outputfile = arg
print ('Input file is "', inputfile)
print ('Output file is "', outputfile)



#calDAV setup
caldav_url = 'https://www.kuhl-mann.de/nextcloud/remote.php/dav'
username = 'Justus'
password = 'Alphabeth1forB2;'
timezone = [2,0]

timeout = 5

f = open("./calendarlib.p")

server_reached = True
client_established = True

print("Looking for server...")
try:
	request = requests.get(caldav_url, timeout=timeout)
except (requests.ConnectionError, requests.Timeout) as exception:
    print("didn't find server, showing data from last successful connection")
    server_reached = False
else:
    print("found server")


try:
    client = caldav.DAVClient(url=caldav_url, username=username, password=password)
except (Exception) as ex:
    client_established = False

if(server_reached and client_established):
    print("Successfully connected to server, starting to download calendars...")
    my_principal = client.principal()
    calendars = my_principal.calendars()

    time_events = []
    day_events = []
    birthdays = []
    for c in calendars:
        current_calendar = my_principal.calendar(name=c.name)
        events_fetched = current_calendar.date_search(
        start=datetime.today()-timedelta(days = datetime.today().weekday()), end=datetime.today()+timedelta(days = 6-datetime.today().weekday()), expand=True)

        if len(events_fetched)> 0:
            for event in events_fetched:
                event_start_str = str(event.vobject_instance.vevent.dtstart)[10:-1]
                event_end_str = str(event.vobject_instance.vevent.dtend)[8:-1]
                
                if(event_start_str.startswith("VALUE")):
                    day_events.append({
                        "DATE":date(int(event_start_str.split("}")[1].split("-")[0]),int(event_start_str.split("}")[1].split("-")[1]),int(event_start_str.split("}")[1].split("-")[2])),
                        "SUMMARY":str(event.vobject_instance.vevent.summary.value), 
                        "CALENDAR":c.name
                        })
                else:
                    sd = event_start_str.split(" ")[0]
                    st = event_start_str.split(" ")[1]
                    sh = int(st.split(":")[0])+timezone[0]+int(st.split(":")[2][2:4])
                    sm = int(st.split(":")[1])+timezone[1]+int(st.split(":")[3])
                    ss = int(st.split(":")[2][0:1])
                    ed = event_end_str.split(" ")[0]
                    et = event_end_str.split(" ")[1]
                    eh = int(et.split(":")[0])+timezone[0]+int(st.split(":")[2][2:4])
                    em = int(et.split(":")[1])+timezone[1]+int(et.split(":")[3])
                    es = int(et.split(":")[2][0:1])
                    time_events.append({
                        "START":datetime(int(sd.split("-")[0]),int(sd.split("-")[1]),int(sd.split("-")[2]), hour = sh, minute = sm, second = ss),
                        "END":datetime(int(ed.split("-")[0]),int(ed.split("-")[1]),int(ed.split("-")[2]), hour = eh, minute = em, second = es),
                        "SUMMARY":str(event.vobject_instance.vevent.summary.value), 
                        "CALENDAR":c.name
                        })
    for event in day_events:
        if event["CALENDAR"] == "Geburtstage von Kontakten":
            pieces = event["SUMMARY"].split(" ")
            age = date.today().year - int(pieces[2][2:-1])
            event["SUMMARY"] = pieces[1]+" "+pieces[0][:-1]+" ("+str(age)+")"
            birthdays.append(event)
            day_events.remove(event)
    print("Download complete")
    calendarlib = {"DAY_EVENTS":day_events,"TIME_EVENTS":time_events,"BIRTHDAYS":birthdays}
    #f = open("./calendarlib.p")
    p.dump( calendarlib, open( "calendarlib.p", "wb" ))
    f.close()
else:
    print("Loading caldata from last time...")
    calendarlib = p.load(open("calendarlib.p","rb"))
    time_events = calendarlib["TIME_EVENTS"]
    day_events = calendarlib["DAY_EVENTS"]
    birthdays = calendarlib["BIRTHDAYS"]


#get principal file

print(birthdays)
print(day_events)
print(time_events)

#with this information now the week calendar can be painted on a b/w 800x480 bitmap.

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

#define fonts to be used
eventfont = ImageFont.truetype("./resource/bf_mnemonika_regular.ttf", 16)
weekdayfont = ImageFont.truetype("./resource/bf_mnemonika_regular.ttf", 16)
timefont = ImageFont.truetype("./resource/bf_mnemonika_regular.ttf", 12)

#create image buffer
Himage = Image.new('1', (800,480), 255)  # 255: clear the frame
draw = ImageDraw.Draw(Himage)

#define language, and if abbreviations for weekdays should be used
language = "EN"
weekday_l_key = "FULL"
draw_date = True
#define grid coordinates
upper_border_grid = 0
lower_border_grid = 465
left_border_grid = 15
right_border_grid = 785
first_hour = 6
last_hour = 23

#calculate some grid related stuff
hours_in_day = last_hour-first_hour
width_grid = right_border_grid-left_border_grid
width_day = round(width_grid/7)
height_grid = lower_border_grid-upper_border_grid
weekday_height = weekdayfont.getsize("Monday")[1]
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

for j in range(len(weekdays[language][weekday_l_key])):
    if draw_date:
        if(max([(weekdayfont.getsize(i+", "+str((monday+timedelta(days=j)).day)+"."+str((monday+timedelta(days=j)).month)+".")[0]>width_day-7) for i in weekdays[language]["FULL"]])):
            weekday_l_key = "SHORT"
        draw.text((left_border_grid+j*width_day+5, upper_border_grid), (weekdays[language][weekday_l_key][j]+", "+str((monday+timedelta(days=j)).day)+"."+str((monday+timedelta(days=j)).month)+"."), font = weekdayfont, fill = 0)
    else:
        if(max([(weekdayfont.getsize(i)[0]>width_day-7) for i in weekdays[language]["FULL"]])):
            weekday_l_key = "SHORT"
        draw.text((left_border_grid+j*width_day+5, upper_border_grid), weekdays[language][weekday_l_key][j], font = weekdayfont, fill = 0)


#draw a grid
draw.line([(left_border_grid, upper_border_grid+weekday_height+2),(right_border_grid, upper_border_grid+weekday_height+2)], fill=0, width=2)
for y in range(width_day,width_grid,width_day):
    draw.line([(y+left_border_grid, upper_border_grid),(y+left_border_grid, lower_border_grid)], fill=0, width=2)

for y in range(upper_border_grid+weekday_height+2,lower_border_grid,two_hour_space):
    for x in range(left_border_grid, right_border_grid, 6):
            draw.line([(x, y), (x+2, y)], fill = 0, width = 1)

#draw times for orientation
i = 0
for y in range(upper_border_grid+weekday_height+4,lower_border_grid,two_hour_space):
    draw.text((left_border_grid-timefont.getsize(str(i*2+first_hour))[0], y), str(i*2+first_hour), font = timefont, fill = 0)
    i +=1

events_on_weekday = [0,0,0,0,0,0,0]

known_calendars = {"DLRG Kalendar" : "DLRG", "Uni Kalendar" : "UNI", "Persönlich" : "PER"}

for event in day_events:
    row = width_day*event["DATE"].weekday()+left_border_grid+4
    if event["CALENDAR"] in known_calendars:
        cal = known_calendars[event["CALENDAR"]]
    else:
        cal = event["CALENDAR"]
    if(events_on_weekday[event["DATE"].weekday()]== 0):
        draw.rectangle((row,upper_border_grid+weekday_height+5,row+width_day-6,lower_border_grid-1),fill = 255)
        draw.line([(row,upper_border_grid+weekday_height+5),(row,lower_border_grid-1)], width = 4, fill = 0)
        draw.line([(row,lower_border_grid-2),(row+width_day-6,lower_border_grid-2)], width = 2, fill = 0)
        draw.line([(row,upper_border_grid+weekday_height+5),(row+width_day-6,upper_border_grid+weekday_height+5)], width = 2, fill = 0)
        draw.line([(row+width_day-7,upper_border_grid+weekday_height+5),(row+width_day-7,lower_border_grid-1)], width = 2, fill = 0)
        wi, hi = eventfont.getsize (event["SUMMARY"])
        draw_text_90_into("["+cal+"] "+event["SUMMARY"], Himage, (row+4,height_grid-(weekday_height+5)-round(wi/2)))
    else:
        wi, hi = eventfont.getsize(event["SUMMARY"])
        draw.line([(row+6+hi,upper_border_grid+weekday_height+9),(row+6+hi,lower_border_grid-4)], width = 2, fill = 0)
        draw_text_90_into("["+cal+"] "+event["SUMMARY"], Himage, (row+10+hi,-round(wi/2)))    
    events_on_weekday[event["DATE"].weekday()] += 1

for event in time_events:
    #draw rectangle
    #find the place via day and time to coordinate conversion
    
    row_start = width_day*event["START"].weekday()+left_border_grid+4
    row_end = width_day*event["END"].weekday()+left_border_grid+4
    left_border_event = row_start+(events_on_weekday[event["START"].weekday()]*(6+(eventfont.getsize(event["SUMMARY"])[1])))
    right_border_event = row_start+width_day-6-((events_on_weekday[event["START"].weekday()])>0)*3
    upper_border_event = round(upper_border_grid+weekday_height+5+((lower_border_grid-(upper_border_grid+weekday_height+5))/hours_in_day)*(event["START"].hour-first_hour+(event["START"].minute/60)))
    lower_border_event = round(upper_border_grid+weekday_height+5+((lower_border_grid-(upper_border_grid+weekday_height+5))/hours_in_day)*(event["END"].hour-first_hour+(event["END"].minute/60)))
    #blank out everything
    if (row_start == row_end): 
        draw.rectangle((left_border_event,upper_border_event,right_border_event,lower_border_event),fill = 255)
    else:
        
        for d in range(event["START"].weekday()+1,event["END"].weekday()):
            draw.rectangle((left_border_event+(d*width_day),upper_border_grid+weekday_height+5,right_border_event+(d*width_day),lower_border_grid),fill = 255)
            draw.line([(left_border_event+(d*width_day),upper_border_grid+weekday_height+5),(left_border_event+(d*width_day),lower_border_grid-1)], width = 4, fill = 0)
            draw.line([(right_border_event-1+(d*width_day),lower_border_grid-2),(right_border_event-1+(d*width_day),lower_border_grid-2)], width = 2, fill = 0)

    #draw borders
    draw.line([(left_border_event,upper_border_event),(left_border_event, min(lower_border_event,lower_border_grid))], width = 4, fill = 0)
    if(lower_border_event<lower_border_grid):
        draw.line([(left_border_event,lower_border_event),(right_border_event,lower_border_event)], width = 2, fill = 0)
    draw.line([(left_border_event,upper_border_event),(right_border_event,upper_border_event)], width = 2, fill = 0)
    draw.line([(right_border_event-1,upper_border_event),(right_border_event-1,min(lower_border_event,lower_border_grid))], width = 2, fill = 0)
    #use abbreviations for some calendars...
    if event["CALENDAR"] in known_calendars:
        cal = known_calendars[event["CALENDAR"]]
    else:
        cal = event["CALENDAR"]
    wi,hi = eventfont.getsize(event["SUMMARY"])
    #format event title, calendar and time to fit into the rectangle
    if(lower_border_event-upper_border_event-2 < hi):
        cropped_ev_str = ('{:2d}'.format(event["START"].hour)+":"+'{:02d}'.format(event["START"].minute)+ " " +event["SUMMARY"])
        while (eventfont.getsize(cropped_ev_str)[0] > right_border_event-left_border_event-4):
            cropped_ev_str = cropped_ev_str[:-1]
        draw.text((left_border_event+6, lower_border_event+4),cropped_ev_str, font = eventfont, fill = 0)
    
    elif(lower_border_event-upper_border_event-2 < hi*2):
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
now_row = width_day*datetime.now().weekday()+left_border_grid
now_time = round(upper_border_grid+weekday_height+5+(((last_hour_line-(upper_border_grid+weekday_height+5))/(hours_in_day-(hours_in_day%2)))*(datetime.now().hour-first_hour+(datetime.now().minute/60))))
if(now_time < lower_border_grid and now_time > upper_border_grid+weekday_height+2):
    draw.line([(now_row,now_time),(now_row+width_day-2,now_time)], width = 2, fill = 0)
    draw.ellipse((now_row, now_time, now_row+10, now_time+4), fill = 0)

#draw warnings, if something went wrong with the connection
if(not server_reached):
    Himage.paste(Image.open("./resource/server_unreachable.png"), (right_border_grid-40,lower_border_grid-40))
if(not client_established):
    Himage.paste(Image.open("./resource/unauthorized.png"), (right_border_grid-40,lower_border_grid-40))
Himage.save("./canvas.bmp")

