import os
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
from io import BytesIO
import re
from dotenv import load_dotenv


load_dotenv()

# CONFIG

BACKEND_URL = os.getenv("BACKEND_URL")

BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

st.set_page_config(
    page_title="TutorRAG",
    page_icon="🎓",
    layout="wide",
)


# SESSION STATE INIT

def init_state():
    defaults = {
        "page": "landing",
        "authenticated": False,
        "username": "",
        "password": "",
        "role": "",
        "grade": 0,
        "chat_messages": [],
        "generated_quiz": None,
        "quiz_result": None,
        "quiz_history": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

init_state()


# HELPERS

def auth():
    return HTTPBasicAuth(
        st.session_state.username,
        st.session_state.password,
    )

def api(method, path, **kwargs):
    return requests.request(
        method,
        f"{BACKEND_URL}{path}",
        auth=auth(),
        timeout=60,
        **kwargs
    )

def logout():
    for k in list(st.session_state.keys()):
        del st.session_state[k]


# LANDING PAGE

def landing_page():
    col1, col2 = st.columns([1.3, 1])

    with col1:
        st.markdown("## 🎓 TutorRAG")
        st.markdown(
            """
            ### AI-Powered Learning From Your Own Documents

            - Upload textbooks & notes  
            - Ask questions using AI  
            - Generate quizzes automatically  
            - Track learning progress  

            **Built using RAG + LLMs**
            """
        )

        b1, b2 = st.columns(2)
        with b1:
            if st.button("🚀 Get Started", use_container_width=True):
                st.session_state.page = "signup"
        with b2:
            if st.button("🔐 Login", use_container_width=True):
                st.session_state.page = "login"

    with col2:
        img = os.path.join(ASSETS_DIR, "landing-page.jpg")

        if os.path.exists(img):
            st.image(img, width="stretch")


# LOGIN PAGE

def login_page():
    col1, col2 = st.columns([1, 1])

    with col1:
        img = os.path.join(ASSETS_DIR, "login.jpg")

        if os.path.exists(img):
            st.image(img, width="stretch")

    with col2:
        st.markdown("## 🔐 Login")

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                r = requests.get(
                    f"{BACKEND_URL}/login",
                    auth=HTTPBasicAuth(username, password),
                )
                if r.status_code == 200:
                    data = r.json()
                    st.session_state.update({
                        "authenticated": True,
                        "username": username,
                        "password": password,
                        "role": data["role"],
                        "grade": data.get("grade", 0),
                        "page": "app",
                    })
                    st.success("Login successful")
                else:
                    st.error("Invalid credentials")

        if st.button("⬅ Back"):
            st.session_state.page = "landing"


# SIGNUP PAGE

def signup_page():
    col1, col2 = st.columns([1, 1])

    with col1:
        img = os.path.join(ASSETS_DIR, "signup.png")

        if os.path.exists(img):
            st.image(img, width="stretch")

    with col2:
        st.markdown("## ✍️ Create Account")
        role = st.selectbox("I am a", ["Student", "Teacher"])

        with st.form("signup_form"):
            full_name = st.text_input("Full Name")
            email = st.text_input("Email")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            if role == "Student":
                grade = st.number_input("Grade", 1, 12)
                school = st.text_input("School")

            submitted = st.form_submit_button("Create Account")

            if submitted:
                endpoint = "/signup/student" if role == "Student" else "/signup/teacher"
                payload = {
                    "fullName": full_name,
                    "email": email,
                    "userName": username,
                    "password": password,
                }
                if role == "Student":
                    payload.update({"grade": grade, "school": school})

                r = requests.post(
                    f"{BACKEND_URL}{endpoint}",
                    json=payload,
                )

                if r.status_code == 200:
                    st.success("Account created successfully")
                else:
                    st.error(r.text)

        if st.button("⬅ Back"):
            st.session_state.page = "landing"


# TEACHER DASHBOARD

def teacher_dashboard():
    img = os.path.join(ASSETS_DIR, "teacher.jpg")

    if os.path.exists(img):
        st.image(img, width=220)
    st.markdown("## 📚 Upload Study Material")

    pdf = st.file_uploader("Upload PDF", type="pdf")
    grade = st.number_input("Grade", 1, 12)

    if st.button("Upload Document", disabled=not pdf):
        with st.spinner("Uploading and indexing..."):
            files = {
                "file": (
                    pdf.name,
                    BytesIO(pdf.getvalue()),
                    "application/pdf",
                )
            }
            data = {"grade": str(int(grade))}
            r = api("POST", "/upload_docs", files=files, data=data)

            if r.status_code == 200:
                st.success("Document uploaded successfully")
            else:
                st.error(r.text)


# STUDENT DASHBOARD

def student_dashboard():
    img = os.path.join(ASSETS_DIR, "students.jpg")

    if os.path.exists(img):
        st.image(img, width=220)

    chat_tab, quiz_tab, history_tab = st.tabs(
        ["💬 Ask Questions", "📝 Quiz Generator", "📜 Quiz History"]
    )

    # ---------------- CHAT ----------------
    with chat_tab:
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ask a question"):
            st.session_state.chat_messages.append(
                {"role": "user", "content": prompt}
            )

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    r = api("POST", "/chat", json={"query": prompt})
                    if r.status_code == 200:
                        data = r.json()
                        answer = data["answer"]
                        if data["sources"]:
                            answer += "\n\n**Sources:** " + ", ".join(data["sources"])
                        st.markdown(answer)
                        st.session_state.chat_messages.append(
                            {"role": "assistant", "content": answer}
                        )
                    else:
                        st.error(r.text)

    # ---------------- QUIZ ----------------
    with quiz_tab:
        if st.session_state.generated_quiz is None:
            topic = st.text_input("Quiz Topic")
            num_q = st.slider("Number of Questions", 1, 10, 3)

            if st.button("Generate Quiz", disabled=not topic):
                r = api(
                    "POST",
                    "/quiz",
                    json={"topic": topic, "num_questions": num_q},
                )
                if r.status_code == 200:
                    st.session_state.generated_quiz = r.json()
                    st.session_state.generated_quiz["topic"] = topic
                    st.session_state.quiz_result = None
                else:
                    st.error(r.text)

        else:
            quiz = st.session_state.generated_quiz
            raw = quiz["quiz"]

            blocks = re.split(r"(Question \d+:)", raw)[1:]
            questions = []

            for i in range(0, len(blocks), 2):
                lines = blocks[i + 1].strip().split("\n")
                q_text = lines[0]
                options = [l for l in lines if re.match(r"[A-Z]\)", l)]
                questions.append({"q": q_text, "opts": options})

            with st.form("quiz_form"):
                answers = []

                for i, q in enumerate(questions):
                    st.markdown(f"**Q{i+1}. {q['q']}**")
                    choice = st.radio(
                        "Choose:",
                        [o[0] for o in q["opts"]],
                        format_func=lambda x: next(
                            o for o in q["opts"] if o.startswith(x)
                        ),
                        key=f"quiz_q{i}",
                    )
                    answers.append(choice)

                submitted = st.form_submit_button("Submit Quiz")

            if submitted:
                r = api(
                    "POST",
                    "/quiz/check",
                    json={
                        "quiz_id": quiz["quiz_id"],
                        "answers": answers,
                    },
                )
                if r.status_code == 200:
                    st.session_state.quiz_result = r.json()
                    st.session_state.generated_quiz = None
                else:
                    st.error(r.text)

        if st.session_state.quiz_result:
            res = st.session_state.quiz_result
            st.success(res["message"])

            for r in res["results"]:
                status = "✅ Correct" if r["is_correct"] else "❌ Incorrect"
                st.markdown(
                    f"**Q{r['question_number']} — {status}**  \n"
                    f"Your Answer: **{r['user_answer']}**  \n"
                    f"Correct Answer: **{r['correct_answer']}**"
                )

            if st.button("Start New Quiz"):
                st.session_state.quiz_result = None

    # ---------------- HISTORY ----------------
    with history_tab:
        if st.button("Load History"):
            r = api("GET", "/quiz/history")
            if r.status_code == 200:
                st.session_state.quiz_history = r.json()["history"]
            else:
                st.error(r.text)

        history = st.session_state.quiz_history
        if history:
            for attempt in history:
                score = attempt["score"]
                total = attempt["total"]
                percent = int((score / total) * 100)

                with st.expander(
                    f"{attempt['topic']} — {score}/{total} ({percent}%)"
                ):
                    raw_quiz = attempt["quiz_content"]

                    blocks = re.split(r"(Question \d+:)", raw_quiz)[1:]
                    parsed = []

                    for i in range(0, len(blocks), 2):
                        lines = blocks[i + 1].strip().split("\n")
                        parsed.append({
                            "question": lines[0],
                            "options": [
                                l for l in lines if re.match(r"[A-Z]\)", l)
                            ],
                        })

                    for i, res in enumerate(attempt["results"]):
                        q = parsed[i]
                        st.markdown(f"### Q{i+1}: {q['question']}")

                        for opt in q["options"]:
                            letter = opt[0]
                            if letter == res["correct_answer"]:
                                st.markdown(f"✅ **{opt}** (Correct)")
                            elif letter == res["user_answer"]:
                                st.markdown(f"❌ **{opt}** (Your Answer)")
                            else:
                                st.markdown(opt)

                        st.divider()


# ROUTER

if st.session_state.page == "landing":
    landing_page()
elif st.session_state.page == "login":
    login_page()
elif st.session_state.page == "signup":
    signup_page()
elif st.session_state.page == "app":
    st.sidebar.title("TutorRAG 🎓")
    st.sidebar.success(
        f"{st.session_state.username} ({st.session_state.role})"
    )
    st.sidebar.button("Logout", on_click=logout)

    if st.session_state.role == "Teacher":
        teacher_dashboard()
    else:
        student_dashboard()