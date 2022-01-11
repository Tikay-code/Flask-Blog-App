import requests
import sys

url = sys.argv[1]
postData = {"data": "test"}
response = requests.post(url=url, data=postData)
print (response.text)
