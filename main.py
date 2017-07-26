import sys
import requests
import bs4
from util import *
from datetime import datetime
from dateutil.parser import parse

def main(argv):
    logger = generateLogger("log.log")

    # Load and parse xml data from NOAA
    r = requests.get("http://forecast.weather.gov/MapClick.php?lat=40.4242&lon=-79.8853&FcstType=digitalDWML")
    if r.status_code is not 200:
        logger.error("Error getting xml data from NOAA")
        return
    logger.info("Get xml data from NOAA")
    soup_xml = bs4.BeautifulSoup(r.content, "lxml-xml")

    # Load and parse html data from NOAA
    r = requests.get("http://forecast.weather.gov/MapClick.php?w10=mhgt&w15=vent&AheadHour=0&Submit=Submit&&FcstType=digital&textField1=40.4242&textField2=-79.8853&site=all")
    if r.status_code is not 200:
        logger.error("Error getting html data from NOAA")
        return
    logger.info("Get html data from NOAA")
    soup_html = bs4.BeautifulSoup(r.content, "html.parser")

    # Number of data points (the current one plus the forecast of the next 6 hours)
    n = 7

    # Get name and location
    device_name = "NOAA NWS " + soup_xml.find("city").text
    point = soup_xml.find("point")
    lat = str2float(point["latitude"])
    lng = str2float(point["longitude"])

    # Get current time and construct an epocht time array
    for k in soup_xml.find_all("start-valid-time"):
        time = [datetimeToEpochtime(parse(k.text))/1000]
        break
    for i in range(1, n):
        time.append(time[i-1] + 3600)

    # Parse weather elements
    te = parseXmlValue(soup_xml.find_all("temperature", type="hourly"), n)
    ws = parseXmlValue(soup_xml.find_all("wind-speed", type="sustained"), n)
    ca = parseXmlValue(soup_xml.find_all("cloud-amount", type="total"), n)
    pp = parseXmlValue(soup_xml.find_all("probability-of-precipitation", type="floating"), n)
    hu = parseXmlValue(soup_xml.find_all("humidity", type="relative"), n)
    wd = parseXmlValue(soup_xml.find_all("direction", type="wind"), n)

    # Parse fire weather data
    mh = []
    vr = []
    for k in soup_html.find_all("font"):
        if "Mixing Height" in k.text:
            if len(mh) != 0: continue
            for m in k.parent.find_next_siblings():
                mh.append(m.text)
        elif "Ventilation Rate" in k.text:
            if len(vr) != 0: continue
            for m in k.parent.find_next_siblings():
                vr.append(m.text)
    mh = map(str2float, mh[0:n])
    vr = map(str2float, vr[0:n])

    # Format data for uploading to ESDR
    data_json = {
        "channel_names": [
            "temperature",
            "wind_speed",
            "sky_cover",
            "precipitation_potential",
            "relative_humidity",
            "wind_direction",
            "mixing_height",
            "ventilation_rate"
        ],
        "data": []
    }
    for k in zip(time, te, ws, ca, pp, hu, wd, mh, vr):
        data_json["data"].append(list(k))
    
    # Upload data to ESDR
    product_id = 65
    access_token, user_id = getEsdrAccessToken("auth.json")
    if access_token is not None:
        uploadDataToEsdr(device_name, data_json, product_id, access_token, isPublic=1, latitude=lat, longitude=lng)

    logger.info("-----------------------------------------------------------------------------") 

def parseXmlValue(s, n):
    values = []
    for k in s:
        for m in k.find_all("value"):
            values.append(m.text)
    return map(str2float, values[0:n])

if __name__ == "__main__":
    main(sys.argv)
