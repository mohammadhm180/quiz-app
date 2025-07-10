# 🧠 Python MySQL Quiz Game App

A command-line quiz application where users can:
- Register, login and play matches
- Compete with opponents
- View weekly, monthly, and all-time leaderboard
- Admins can approve questions, ban users, and view stats

## 🚀 Features

✅ User authentication  
✅ Match system with real-time answers  
✅ XP and level tracking  
✅ Leaderboard for weekly, monthly, and all-time  
✅ Admin dashboard  

## 🛠 Tech Stack

- **Python 3**
- **MySQL**
- **bcrypt** for password hashing

## ⚙️ Configuration

in terminal run this command to create a the database

```bash
mysql -u root -p -e "CREATE DATABASE QK;"
```
Run the following commands to set up your tables and triggers:

```bash
mysql -u root -p QK < schema.sql
mysql -u root -p QK < triggers.sql
mysql -u root -p QK < indexes.sql
```


Before running the app, configure your database settings.

### 1. Set your database credentials

Open `main.py` and update the following section with your MySQL credentials:

```python
DB_CONF = {
    'host': 'localhost',
    'user': 'root', # 🔒 Replace with your actual username
    'password': 'your_password',  # 🔒 Replace with your actual MySQL password
    'database': 'QK' # 🔒 Replace with your actual database name
}
```
## 📦 Setup

```bash
git clone https://github.com/mohammadhm180/quiz-app.git
cd quiz-app
pip install -r requirements.txt

