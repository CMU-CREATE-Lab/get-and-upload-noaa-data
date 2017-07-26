from util import *
import requests
import json

access_token, user_id = getEsdrAccessToken("auth.json")
print "access token = " + access_token

headers = {
    "Authorization": "Bearer " + access_token,
    "Content-Type": "application/json"
}
url = "https://esdr.cmucreatelab.org/api/v1/products"
r = requests.post(url, data=json.dumps(loadJson("product.json")), headers=headers)
print "ESDR returns: " + r.content
