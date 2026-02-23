import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "test_db")


client=MongoClient(MONGO_URI)
db=client[DB_NAME]

# User collection
users_collection = db["users"]