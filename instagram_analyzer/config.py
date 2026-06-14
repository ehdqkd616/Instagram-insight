import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_FOLDER = DATA_DIR
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB

ALLOWED_EXTENSIONS = {"json", "zip"}

SESSION_DATA_KEY = "data_session"
