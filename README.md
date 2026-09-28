# 📊💵PocketSmart AI: Your Smart Budget & Recommendation Assistant

PocketSmart AI is an AI-powered personal financial assistant built with **Streamlit** and **Google Gemini AI** to give users tailored budget insights and savings recommendations.

## 📁Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/pocketsmart-ai.git](https://github.com/YOUR_USERNAME/pocketsmart-ai.git)
   cd pocketsmart-ai

2. **Project Structure:**
 ```bash  
   PocketSmart_AI/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── backend/
│   ├── __init__.py
│   ├── database.py
│   ├── calculations.py
│   ├── recommendations.py
│   └── export.py
│
├── frontend/
│   ├── __init__.py
│   ├── dashboard.py
│   ├── income.py
│   ├── expenses.py
│   ├── transactions.py
│   └── styles.py
│
├── data/
│   └── pocketsmart_v2.db
│
├── assets/
│   ├── logo.png
│   └── icons/
│
└── docs/
    ├── project_report.pdf
    └── screenshots/
```
## ⚙️Backend Setup

```
Backend:
Python
SQLite Database
Financial calculations
Budget calculation
Financial health score
Recommendation engine
CSV import/export
```
**⚙️Main Backend Scripts:**

```
# database.py
import sqlite3

DB_NAME = "data/pocketsmart_v2.db"

def get_connection():
    return sqlite3.connect(DB_NAME)
```

```
# calculations.py
def calculate_balance(income, expenses):
    return income - expenses

def calculate_savings_rate(income, expenses):
    if income <= 0:
        return 0
    return ((income - expenses) / income) * 100
```

## 🖥️Frontend Setup
```
Frontend:
Tkinter GUI
Dashboard
Income section
Expense section
Balance display
Budget progress
Health score
Expense chart
Transaction history
CSV Import/Export
```


## 🔬Lab Environment Setup

```
git clone https://github.com/naveenprasad23042008-coder/PocketSmart_AI.git

cd PocketSmart_AI

python -m venv venv
```

**🪟Windows:**

```
venv\Scripts\activate
```

**📦Install Packages:**

```
pip install -r requirements.txt
```

**🏃Run:**

```
python app.py
```

## 🚀Development Scripts

```
# scripts/run.py

import subprocess

subprocess.run(["python", "app.py"])
```

```
# scripts/init_database.py

import sqlite3

conn = sqlite3.connect("data/pocketsmart_v2.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS income(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    date TEXT NOT NULL,
    note TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    date TEXT NOT NULL,
    note TEXT
)
""")

conn.commit()
conn.close()

print("Database initialized successfully.")
```
