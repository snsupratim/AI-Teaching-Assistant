from pydantic import BaseModel


class StudentUser(BaseModel):
    # id:int
    fullname:str
    email:str
    username:str
    password:str
    grade:int
    school:str


class TeacherUser(BaseModel):
    # id:int
    fullname:str
    email:str
    username:str
    password:str
    school:str