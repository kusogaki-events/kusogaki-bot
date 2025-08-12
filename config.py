from os import getenv

from dotenv import load_dotenv

load_dotenv()

TOKEN = getenv('TOKEN')
TEST_TOKEN = getenv('TEST_TOKEN')
STAFF_ROLE_ID = getenv('STAFF_ROLE_ID')
AWAIZ_USER_ID = getenv('AWAIZ_USER_ID')
MONGO_URI = getenv('MONGO_URI')
DB_NAME = getenv('DB_NAME')
