# python script to display the weather as an icon on an e-paper screen
from datetime import datetime
import requests
import json
from PIL import Image,ImageDraw,ImageFont

# example for brightsky API suage for the 10th of Sept. in Münster
# https://api.brightsky.dev/weather?lat=52&lon=7.6&date=2022-09-10

today = datetime.today()
print(today.strftime("%Y-%m-%d"))
url = "https://api.brightsky.dev/weather?lat=52&lon=7.6&date="+today.strftime("%Y-%m-%d") # "https://api.covid19api.com/summary"
response = requests.get(url).text
response_info = json.loads(response)
temps = []
for w in response_info["weather"]:
    time = datetime.fromisoformat(w["timestamp"])
    print(time)
    # print(w)
    precs.append(w['precipitation'])
    w['sunshine']
    temps.append(w['temperature'])
    w['wind_direction']
    w['wind_speed']
    w['cloud_cover']
    w['wind_gust_speed']
    w['condition']
    w['icon']

Himage = Image.new('1', (800,480), 255)  # 255: clear the frame
draw = ImageDraw.Draw(Himage)

Himage.paste(Image.open("./resource/server_unreachable.png"), (400,240))
    

