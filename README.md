# 💧 INGRES Groundwater AI Chatbot

An AI-powered chatbot that allows users to query groundwater data using natural language.
It converts user questions into SQL queries using an LLM and retrieves insights from a real groundwater dataset.

---

## 🚀 Features

* 💬 Chat with groundwater data using natural language
* 🧠 LLM-powered SQL query generation (LangChain + Groq)
* 📊 Works on real-world groundwater datasets (multi-year)
* ⚡ FastAPI backend for API handling
* 🎨 React-based chat interface
* 🔄 End-to-end pipeline: Excel → CSV → SQLite → AI

---

## 🛠️ Tech Stack

### Backend

* Python
* FastAPI
* SQLite
* LangChain
* Groq LLM (LLaMA 3)

### Frontend

* React (Vite)
* Axios

### Data Processing

* Pandas
* Excel → CSV pipeline

---

## 📂 Project Structure

```
INGRES-ChatBot/
│
├── backend/                # FastAPI + AI chatbot logic
│   ├── main.py
│   └── chatbot.py
│
├── frontend/               # React chat UI
│   └── src/
│
├── data/
│   └── raw_excel/          # Original datasets
│
├── processed_data/         # Cleaned datasets
│
├── notebooks/              # Data preprocessing scripts
│
├── groundwater.db          # SQLite database
├── .env                    # API keys (ignored)
├── .gitignore
└── README.md
```

---

## ⚙️ Setup Instructions

### 🔹 1. Clone Repository

```
git clone https://github.com/your-username/INGRES-ChatBot.git
cd INGRES-ChatBot
```

---

### 🔹 2. Backend Setup

```
cd backend
pip install -r ../requirements.txt
uvicorn main:app --reload
```

Backend runs at:

```
http://127.0.0.1:8000
```

---

### 🔹 3. Frontend Setup

```
cd frontend
npm install
npm run dev
```

Frontend runs at:

```
http://localhost:5173
```

---

## 🔐 Environment Variables

Create a `.env` file in the root directory:

```
GROQ_API_KEY=your_groq_api_key
```

> ⚠️ Never commit `.env` to GitHub

---

## 📊 Example Queries

Try asking:

* "Which state has highest groundwater availability?"
* "Top 10 districts by groundwater recharge"
* "Compare rainfall and groundwater availability"
* "Show trends over years"

---

## 🧠 How It Works

1. User enters a question in the React UI
2. Request is sent to FastAPI backend
3. LangChain agent converts question → SQL query
4. SQLite database is queried
5. Result is returned as a natural language response

---

## 📈 Future Improvements

* 📊 Add data visualization (charts/graphs)
* 💾 Chat history & session memory
* 🌐 Deploy backend & frontend
* 🔍 Advanced filtering and analytics
* 🔐 Authentication system

---

## 🤝 Contributors

* Sreekanth Teegala
* Your Teammate Name

---

## 📄 License

This project is for educational and demonstration purposes.

---

## ⭐ If you like this project

Give it a star ⭐ and feel free to fork!
