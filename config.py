from os import getenv

from dotenv import load_dotenv

NORMAL_COLOR = 0x2B2D31
INFORMATION_COLOR = 0x546E7A
WARNING_COLOR = 0xE67E22
ERROR_COLOR = 0xE74C3C

load_dotenv()

TOKEN = getenv('TOKEN')
STAFF_ROLE_ID = getenv('STAFF_ROLE_ID')
