import sys
import requests
import bs4
from util import *
from datetime import datetime
from dateutil.parser import parse

def main(argv):
    logger = generateLogger("log.log")
    logger.info("==============================================================================")

    # The order of the urls means:
    # 1. Swissvale PA
    # 2. Pittsburgh, PA
    # 3. Bloomfield PA
    # 4. Clairton PA
    # 5. Braddock PA
    xml_urls = [
        "http://forecast.weather.gov/MapClick.php?lat=40.4242&lon=-79.8853&FcstType=digitalDWML",
        "http://forecast.weather.gov/MapClick.php?lat=40.4385&lon=-79.9973&FcstType=digitalDWML",
        "http://forecast.weather.gov/MapClick.php?lat=40.4457&lon=-79.9546&FcstType=digitalDWML",
        "http://forecast.weather.gov/MapClick.php?lat=40.2965&lon=-79.8939&FcstType=digitalDWML",
        "http://forecast.weather.gov/MapClick.php?lat=40.4034&lon=-79.8684&FcstType=digitalDWML"
    ]
    html_urls = [
        "http://forecast.weather.gov/MapClick.php?w10=mhgt&w15=vent&AheadHour=0&Submit=Submit&&FcstType=digital&textField1=40.4242&textField2=-79.8853&site=all",
        "http://forecast.weather.gov/MapClick.php?w10=mhgt&w15=vent&AheadHour=0&Submit=Submit&&FcstType=digital&textField1=40.4385&textField2=-79.9973&site=all",
        "http://forecast.weather.gov/MapClick.php?w10=mhgt&w15=vent&AheadHour=0&Submit=Submit&&FcstType=digital&textField1=40.4457&textField2=-79.9546&site=all",
        "http://forecast.weather.gov/MapClick.php?w10=mhgt&w15=vent&AheadHour=0&Submit=Submit&&FcstType=digital&textField1=40.2965&textField2=-79.8939&site=all",
        "http://forecast.weather.gov/MapClick.php?w10=mhgt&w15=vent&AheadHour=0&Submit=Submit&&FcstType=digital&textField1=40.4034&textField2=-79.8684&site=all"
    ]

    access_token, user_id = getEsdrAccessToken("auth.json")
    for x, h in zip(xml_urls, html_urls):
        getNoaaData(x, h, access_token)

    logger.info("==============================================================================")

def getNoaaData(xml_url, html_url, access_token):
    logger = generateLogger("log.log")
    logger.info("-----------------------------------------------------------------------------")

    # Load and parse xml data from NOAA
    r = requests.get(xml_url)
    if r.status_code is not 200:
        logger.error("Error getting xml data from NOAA")
        return
    logger.info("Get xml data from NOAA")
    soup_xml = bs4.BeautifulSoup(r.content, "lxml-xml")

    # Load and parse html data from NOAA
    r = requests.get(html_url)
    if r.status_code is not 200:
        logger.error("Error getting html data from NOAA")
        return
    logger.info("Get html data from NOAA")
    soup_html = bs4.BeautifulSoup(r.content, "html.parser")

    # Number of data points (the current one plus the forecast of the next 6 hours)
    n = 48

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

    # Convert degrees F to C
    te = map(lambda x: round((x-32)/1.8, 2), te)

    # Parse fire weather data
    mh = []
    vr = []
    for k in soup_html.find_all("font"):
        if "Mixing Height" in k.text:
            for m in k.parent.find_next_siblings():
                mh.append(m.text)
        elif "Ventilation Rate" in k.text:
            for m in k.parent.find_next_siblings():
                vr.append(m.text)
    mh = map(lambda x: str2float(x, default_value=0), mh[0:n])
    vr = map(lambda x: str2float(x, default_value=0), vr[0:n])

    # Format data for uploading to ESDR
    data_json = {
        "channel_names": [
            "temperature_degrees_c",
            "wind_speed_mph",
            "sky_cover_percentage",
            "precipitation_potential_percentage",
            "relative_humidity_percentage",
            "wind_direction_degrees_true",
            "mixing_height_x100_ft",
            "ventilation_rate_x1000_mph_ft"
        ],
        "data": []
    }
    for k in zip(time, te, ws, ca, pp, hu, wd, mh, vr):
        data_json["data"].append(list(k))

    # Upload data to ESDR
    product_id = 66
    logger.info("Upload data: " + json.dumps(data_json))
    if access_token is not None:
        uploadDataToEsdr(device_name, data_json, product_id, access_token, isPublic=1, latitude=lat, longitude=lng)

def parseXmlValue(s, n):
    values = []
    for k in s:
        for m in k.find_all("value"):
            values.append(m.text)
    return map(lambda x: str2float(x, default_value=0), values[0:n])

if __name__ == "__main__":
    main(sys.argv)
