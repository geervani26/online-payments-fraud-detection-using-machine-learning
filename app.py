# ----------------------------------------
# IMPORT LIBRARIES
# ----------------------------------------
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
import numpy as np
import pickle
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

# ----------------------------------------
# LOAD TRAINED MODEL
# ----------------------------------------
model = pickle.load(open("model/payments.pkl", "rb"))

# ----------------------------------------
# CREATE FLASK APP
# ----------------------------------------
app = Flask(__name__)
app.secret_key = 'your_secret_key_here_change_this_in_production_2024'  # Change this to a random secret key

# ----------------------------------------
# CONTEXT PROCESSOR FOR TEMPLATES
# ----------------------------------------
@app.context_processor
def utility_processor():
    return {'now': datetime.now}

# ----------------------------------------
# DATABASE INITIALIZATION WITH MIGRATION
# ----------------------------------------
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Check if users table exists
    c.execute("""SELECT name FROM sqlite_master WHERE type='table' AND name='users'""")
    table_exists = c.fetchone()
    
    if not table_exists:
        # Create new users table
        c.execute('''CREATE TABLE users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT UNIQUE NOT NULL,
                      password TEXT NOT NULL,
                      email TEXT,
                      full_name TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        print("Created new users table with all columns")
    else:
        # Check existing columns
        c.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in c.fetchall()]
        print(f"Existing columns: {columns}")
        
        # Add missing columns if they don't exist
        if 'email' not in columns:
            try:
                c.execute("ALTER TABLE users ADD COLUMN email TEXT")
                print("Added email column to users table")
            except sqlite3.OperationalError as e:
                print(f"Note: {e}")
        
        if 'full_name' not in columns:
            try:
                c.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
                print("Added full_name column to users table")
            except sqlite3.OperationalError as e:
                print(f"Note: {e}")
        
        if 'created_at' not in columns:
            try:
                c.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP")
                print("Added created_at column to users table")
                # Update existing rows with current timestamp
                c.execute("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
                print("Updated created_at for existing rows")
            except sqlite3.OperationalError as e:
                print(f"Note: {e}")
    
    # Create transactions table if not exists
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  step INTEGER,
                  type TEXT,
                  amount REAL,
                  oldbalanceOrg REAL,
                  newbalanceOrig REAL,
                  oldbalanceDest REAL,
                  newbalanceDest REAL,
                  result TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Create chat messages table if not exists
    c.execute('''CREATE TABLE IF NOT EXISTS chat_messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  message TEXT,
                  response TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    conn.commit()
    conn.close()
    print("Database initialization complete")

# Initialize database
init_db()

# ----------------------------------------
# HOME PAGE
# ----------------------------------------
@app.route("/")
def home():
    return render_template("home.html")

# ----------------------------------------
# REGISTER PAGE
# ----------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form.get("email", "")
        full_name = request.form.get("full_name", "")
        
        # Hash the password
        hashed_password = generate_password_hash(password)
        
        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password, email, full_name) VALUES (?, ?, ?, ?)",
                      (username, hashed_password, email, full_name))
            conn.commit()
            conn.close()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists!", "error")
            return render_template("register.html")
    
    return render_template("register.html")

# ----------------------------------------
# LOGIN PAGE
# ----------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            session['user'] = username
            session['user_id'] = user[0]
            # Handle if full_name doesn't exist yet
            session['full_name'] = user[4] if len(user) > 4 and user[4] else username
            session['user_email'] = user[3] if len(user) > 3 and user[3] else ""
            flash(f"Welcome back, {session['full_name']}! Login successful.", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password!", "error")
            return render_template("login.html")
    
    return render_template("login.html")

# ----------------------------------------
# LOGOUT
# ----------------------------------------
@app.route("/logout")
def logout():
    username = session.get('full_name', session.get('user', 'User'))
    session.pop('user', None)
    session.pop('user_id', None)
    session.pop('full_name', None)
    session.pop('user_email', None)
    flash(f"Goodbye, {username}! You have been logged out.", "success")
    return redirect(url_for('home'))

# ----------------------------------------
# PROFILE PAGE
# ----------------------------------------
@app.route("/profile")
def profile():
    if 'user' not in session:
        flash("Please login to view profile!", "error")
        return redirect(url_for('login'))
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Get user data
        c.execute("SELECT username, email, full_name, created_at FROM users WHERE id = ?", (session['user_id'],))
        user_data = c.fetchone()
        conn.close()
        
        # If user_data has None values, provide defaults
        if user_data:
            user_data = list(user_data)
            for i in range(len(user_data)):
                if user_data[i] is None:
                    if i == 1:  # email
                        user_data[i] = ""
                    elif i == 2:  # full_name
                        user_data[i] = session['user']
                    elif i == 3:  # created_at
                        user_data[i] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            # If no user data found, create default
            user_data = [session['user'], "", session['user'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        
        return render_template("profile.html", user=user_data)
    except Exception as e:
        print(f"Profile error: {e}")
        flash("Error loading profile. Please try again.", "error")
        return redirect(url_for('home'))

# ----------------------------------------
# UPDATE PROFILE
# ----------------------------------------
@app.route("/update_profile", methods=["POST"])
def update_profile():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    email = request.form["email"]
    full_name = request.form["full_name"]
    
    if not email or not full_name:
        flash("Please fill in all fields!", "error")
        return redirect(url_for('profile'))
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Update user profile
        c.execute("UPDATE users SET email = ?, full_name = ? WHERE id = ?",
                  (email, full_name, session['user_id']))
        conn.commit()
        conn.close()
        
        # Update session
        session['full_name'] = full_name
        session['user_email'] = email
        
        flash("✅ Profile updated successfully!", "success")
    except Exception as e:
        print(f"Update profile error: {e}")
        flash("Error updating profile. Please try again.", "error")
    
    return redirect(url_for('profile'))

# ----------------------------------------
# DASHBOARD
# ----------------------------------------
@app.route("/dashboard")
def dashboard():
    if 'user' not in session:
        flash("Please login to view dashboard!", "error")
        return redirect(url_for('login'))
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Get user's transaction history
        c.execute("""SELECT type, amount, result, timestamp FROM transactions 
                     WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50""", 
                  (session['user_id'],))
        transactions = c.fetchall()
        
        # Get statistics
        c.execute("""SELECT COUNT(*) FROM transactions WHERE user_id = ?""", (session['user_id'],))
        total_transactions = c.fetchone()[0] or 0
        
        c.execute("""SELECT COUNT(*) FROM transactions WHERE user_id = ? AND result = 'Fraudulent Transaction'""", 
                  (session['user_id'],))
        fraud_count = c.fetchone()[0] or 0
        
        c.execute("""SELECT SUM(amount) FROM transactions WHERE user_id = ?""", (session['user_id'],))
        total_amount = c.fetchone()[0] or 0
        
        conn.close()
        
        # Calculate fraud percentage
        fraud_percentage = (fraud_count / total_transactions * 100) if total_transactions > 0 else 0
        
        # Prepare chart data
        chart_labels = []
        chart_data = []
        for t in transactions[:10]:  # Last 10 transactions for chart
            if t[3]:  # timestamp exists
                try:
                    chart_labels.append(t[3][:10])  # Just the date part
                except:
                    chart_labels.append("Unknown")
            else:
                chart_labels.append("Unknown")
            chart_data.append(float(t[1]) if t[1] else 0)
        
        return render_template("dashboard.html", 
                              transactions=transactions,
                              total_transactions=total_transactions,
                              fraud_count=fraud_count,
                              total_amount=f"{total_amount:,.2f}",
                              fraud_percentage=round(fraud_percentage, 2),
                              chart_labels=json.dumps(chart_labels[::-1]),
                              chart_data=json.dumps(chart_data[::-1]))
    except Exception as e:
        print(f"Dashboard error: {e}")
        flash("Error loading dashboard. Please try again.", "error")
        return redirect(url_for('home'))

# ----------------------------------------
# DASHBOARD API FOR REAL-TIME UPDATES
# ----------------------------------------
@app.route("/api/dashboard-stats")
def dashboard_stats():
    if 'user' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        c.execute("""SELECT COUNT(*) FROM transactions WHERE user_id = ?""", (session['user_id'],))
        total_transactions = c.fetchone()[0] or 0
        
        c.execute("""SELECT COUNT(*) FROM transactions WHERE user_id = ? AND result = 'Fraudulent Transaction'""", 
                  (session['user_id'],))
        fraud_count = c.fetchone()[0] or 0
        
        c.execute("""SELECT SUM(amount) FROM transactions WHERE user_id = ?""", (session['user_id'],))
        total_amount = c.fetchone()[0] or 0
        
        conn.close()
        
        fraud_percentage = (fraud_count / total_transactions * 100) if total_transactions > 0 else 0
        
        return jsonify({
            "total_transactions": total_transactions,
            "fraud_count": fraud_count,
            "total_amount": f"{total_amount:,.2f}",
            "fraud_percentage": round(fraud_percentage, 2)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------------------------
# CHATBOT PAGE
# ----------------------------------------
@app.route("/chatbot")
def chatbot():
    if 'user' not in session:
        flash("Please login to use chatbot!", "error")
        return redirect(url_for('login'))
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("""SELECT message, response, timestamp FROM chat_messages 
                     WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50""", 
                  (session['user_id'],))
        chat_history = c.fetchall()
        conn.close()
        
        return render_template("chatbot.html", chat_history=chat_history)
    except Exception as e:
        print(f"Chatbot error: {e}")
        flash("Error loading chatbot. Please try again.", "error")
        return redirect(url_for('home'))

# ----------------------------------------
# CHATBOT API
# ----------------------------------------
@app.route("/chatbot_api", methods=["POST"])
def chatbot_api():
    if 'user' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        
        if not user_message:
            return jsonify({"response": "Please say something!"}), 400
        
        # Generate response
        response = generate_chatbot_response(user_message)
        
        # Save to database
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("""INSERT INTO chat_messages (user_id, message, response) 
                     VALUES (?, ?, ?)""", 
                  (session['user_id'], user_message, response))
        conn.commit()
        conn.close()
        
        return jsonify({
            "response": response, 
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
    except Exception as e:
        print(f"Chatbot API error: {e}")
        return jsonify({"response": "Sorry, I'm having trouble responding right now."}), 500

def generate_chatbot_response(message):
    message = message.lower().strip()
    
    # Greetings
    if any(word in message for word in ['hello', 'hi', 'hey', 'greetings']):
        return "👋 Hello! I'm your fraud detection assistant. How can I help you today?"
    
    # What is fraud detection
    elif 'what is fraud' in message or 'what is fraud detection' in message:
        return "🔍 **Fraud detection** is the process of identifying suspicious transactions that could be fraudulent. Our system uses machine learning to analyze patterns and flag potential fraud in real-time, helping protect users from financial losses."
    
    # How it works
    elif any(phrase in message for phrase in ['how does it work', 'how it works', 'how do you work']):
        return "⚙️ **How our system works:**\n\n1️⃣ You enter transaction details through the form\n2️⃣ Our ML model analyzes 7 key features\n3️⃣ The system compares patterns against known fraud cases\n4️⃣ You get an instant prediction (Fraudulent/Legitimate)\n5️⃣ All transactions are saved to your dashboard for tracking"
    
    # Features analyzed
    elif any(phrase in message for phrase in ['what features', 'what do you analyze', 'what data']):
        return "📊 **Features we analyze:**\n\n• 📅 Step Number (time step)\n• 💳 Transaction Type (PAYMENT, TRANSFER, CASH_OUT, DEBIT, CASH_IN)\n• 💰 Transaction Amount\n• 🏦 Origin Account Old Balance\n• 💵 Origin Account New Balance\n• 🎯 Destination Account Old Balance\n• 💸 Destination Account New Balance"
    
    # Accuracy
    elif any(word in message for word in ['accuracy', 'accurate', 'how reliable']):
        return "🎯 **Accuracy:** Our model has been trained on thousands of transactions and achieves high accuracy in detecting fraudulent patterns. However, no system is 100% perfect. We recommend always reviewing suspicious transactions manually and staying vigilant!"
    
    # Data safety
    elif any(phrase in message for phrase in ['data safe', 'data security', 'privacy', 'secure']):
        return "🔒 **Data Security:**\n\n✅ End-to-end encryption\n✅ No storage of sensitive payment info\n✅ Password hashing for accounts\n✅ Regular security updates\n✅ GDPR compliant practices\n\nYour data is protected and only used for fraud detection!"
    
    # Transaction types
    elif any(phrase in message for phrase in ['transaction types', 'types of transactions']):
        return "💳 **Supported Transaction Types:**\n\n• 💳 PAYMENT - Regular payments\n• 🔄 TRANSFER - Money transfers\n• 💵 CASH_OUT - Cash withdrawals\n• 💳 DEBIT - Debit transactions\n• 💰 CASH_IN - Cash deposits\n\nEach type has different fraud patterns!"
    
    # Help
    elif 'help' in message:
        return "❓ **How can I help you?**\n\nYou can ask me about:\n• 🔍 What is fraud detection?\n• ⚙️ How the system works\n• 📊 Features we analyze\n• 🎯 Accuracy of predictions\n• 🔒 Data security\n• 💳 Transaction types\n• 📈 Dashboard features\n• 👤 Profile management\n\nJust type your question!"
    
    # Dashboard
    elif any(word in message for word in ['dashboard', 'statistics', 'stats']):
        return "📈 **Dashboard Features:**\n\n• View transaction history\n• See fraud statistics\n• Interactive charts\n• Achievement badges\n• Real-time updates\n• Transaction search\n\nClick on 'DASHBOARD' in the navigation menu to access it!"
    
    # Profile
    elif any(word in message for word in ['profile', 'account', 'settings']):
        return "👤 **Profile Management:**\n\n• Update your email\n• Change your full name\n• View member since date\n• Copy user ID\n• Theme preferences\n\nGo to 'PROFILE' in the navigation menu to manage your account!"
    
    # Theme
    elif any(word in message for word in ['theme', 'dark mode', 'light mode', 'cyber']):
        return "🎨 **Theme Options:**\n\n• 🌙 Dark Theme (default)\n• ☀️ Light Theme\n• 💻 Cyber Theme\n\nClick the theme switcher in the top-right corner to change themes!"
    
    # Keyboard shortcuts
    elif any(phrase in message for phrase in ['keyboard', 'shortcuts', 'hotkeys']):
        return "⌨️ **Keyboard Shortcuts:**\n\n• Ctrl + N - Home\n• Ctrl + D - Dashboard\n• Ctrl + C - Chatbot\n• Ctrl + P - Profile\n• ? - Show help\n• Esc - Close help"
    
    # Achievements
    elif any(word in message for word in ['achievement', 'badge', 'trophy']):
        return "🏆 **Achievements:**\n\n• 🔍 First Analysis - Analyze your first transaction\n• 🛡️ Fraud Hunter - Detect 5 frauds\n• 🏆 Expert Analyst - 100 total transactions\n• 🎯 Fraud Detector - Find your first fraud\n\nCheck your progress in the Dashboard!"
    
    # Pricing
    elif any(word in message for word in ['price', 'cost', 'free', 'paid']):
        return "💰 **Pricing:**\n\nGood news! Our fraud detection service is completely **FREE**! 🎉\n\n• No subscription fees\n• No hidden costs\n• Unlimited transactions\n• All features included\n\nWe believe in making financial security accessible to everyone!"
    
    # Thank you
    elif any(word in message for word in ['thank', 'thanks', 'appreciate']):
        return "🙏 You're welcome! I'm glad I could help. Feel free to ask if you have more questions!"
    
    # Bye
    elif any(word in message for word in ['bye', 'goodbye', 'see you']):
        return "👋 Goodbye! Feel free to come back if you need help. Stay safe from fraud!"
    
    # Default response
    else:
        return "🤔 I'm not sure I understand. Try asking about:\n\n• 🔍 Fraud detection\n• ⚙️ How it works\n• 📊 Features\n• 🎯 Accuracy\n• 🔒 Security\n• 💳 Transaction types\n• 📈 Dashboard\n• 👤 Profile\n• 🎨 Themes\n• ⌨️ Shortcuts\n• 🏆 Achievements\n\nOr type 'help' for more options!"

# ----------------------------------------
# PREDICTION LOGIC
# ----------------------------------------
@app.route("/predict", methods=["POST"])
def predict():
    # Check if user is logged in
    if 'user' not in session:
        flash("Please login to analyze transactions!", "error")
        return redirect(url_for('login'))
    
    try:
        # Get values from form
        step = float(request.form["step"])
        
        # Encode transaction type
        type_mapping = {
            "PAYMENT": 0,
            "TRANSFER": 1,
            "CASH_OUT": 2,
            "DEBIT": 3,
            "CASH_IN": 4
        }
        transaction_type = request.form["type"]
        type_ = float(type_mapping[transaction_type])
        
        amount = float(request.form["amount"])
        oldbalanceOrg = float(request.form["oldbalanceOrg"])
        newbalanceOrig = float(request.form["newbalanceOrig"])
        oldbalanceDest = float(request.form["oldbalanceDest"])
        newbalanceDest = float(request.form["newbalanceDest"])

        # Validate balances
        if amount < 0:
            flash("Amount cannot be negative!", "error")
            return redirect(url_for('home'))
        
        if oldbalanceOrg < 0 or newbalanceOrig < 0 or oldbalanceDest < 0 or newbalanceDest < 0:
            flash("Balances cannot be negative!", "error")
            return redirect(url_for('home'))
        
        # Features array
        features = np.array([[step, type_, amount,
                              oldbalanceOrg, newbalanceOrig,
                              oldbalanceDest, newbalanceDest]])

        # Prediction
        prediction = model.predict(features)

        if prediction[0] == 1:
            result = "Fraudulent Transaction"
        else:
            result = "Legitimate Transaction"
        
        # Save transaction to database
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("""INSERT INTO transactions 
                     (user_id, step, type, amount, oldbalanceOrg, newbalanceOrig, 
                      oldbalanceDest, newbalanceDest, result) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (session['user_id'], step, transaction_type, amount, 
                   oldbalanceOrg, newbalanceOrig, oldbalanceDest, newbalanceDest, result))
        conn.commit()
        conn.close()
        
        # Flash success message
        flash(f"Transaction analyzed successfully! Result: {result}", "success")

    except Exception as e:
        print(f"Prediction error: {e}")
        flash("Error analyzing transaction. Please check your inputs.", "error")
        return redirect(url_for('home'))

    return render_template("submit.html", result=result)

# ----------------------------------------
# RESULT PAGE
# ----------------------------------------
@app.route("/result/<result>")
def show_result(result):
    return render_template("predict.html", prediction_text=result)

# ----------------------------------------
# ERROR HANDLERS
# ----------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500

# ----------------------------------------
# RUN APP
# ----------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)