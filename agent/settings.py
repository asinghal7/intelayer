import os
from dotenv import load_dotenv
load_dotenv()

TALLY_URL = os.getenv("TALLY_URL", "http://192.168.1.50:9000")
TALLY_COMPANY = os.getenv("TALLY_COMPANY", "Your Company")
DB_URL = os.getenv("DB_URL", "postgresql://inteluser:change_me@localhost:5432/intelayer")

