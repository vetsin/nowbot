import os

BOT_PREFIX = ('!')
TOKEN = os.environ['TOKEN']
WEBHOOK_TOKEN = os.environ['WEBHOOK_TOKEN']
NOW_INSTANCE = 'https://thetacolab.service-now.com'
NOW_USER = 'tacobot'
NOW_PASS = os.environ['NOW_PASS']
OWNERS = []
BLACKLIST = []


# Bot colors
main_color = 0xD75BF4
error = 0xE02B2B
success = 0x42F56C
warning = 0xF59E42
info = 0x4299F5
