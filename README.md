# PocketSmart AI: Your Smart Budget & Recommendation Assistant

PocketSmart AI is an AI-powered personal financial assistant built with **Streamlit** and **Google Gemini AI** to give users tailored budget insights and savings recommendations.

## Setup Instructions

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
