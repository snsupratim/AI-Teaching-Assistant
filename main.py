from fastapi import FastAPI


app=FastAPI()

@app.get("/")
def health_check():
    return {"status": "tutor-rag is running!"}

# def main():
#     print("Hello from tutor-rag!")


# if __name__ == "__main__":
#     main()
