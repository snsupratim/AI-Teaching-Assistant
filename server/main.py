from fastapi import FastAPI
from auth.route import router as auth_router


app=FastAPI()



app.include_router(auth_router)


@app.get("/")
def home():
    return {"message":"Welcome to the User Management API"}