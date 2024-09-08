from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import sql
import bcrypt
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib

# Load your ML model (ensure you have trained and saved this model)
model = joblib.load('path/to/your_model.pkl')

# Example function to rank users based on their performance
def rank_users():
    # Fetch user performance data from the database
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT user_id, performance_metric FROM challenge_participation')
    data = cur.fetchall()
    cur.close()
    conn.close()
    
    # Convert data to DataFrame
    df = pd.DataFrame(data, columns=['user_id', 'performance_metric'])
    
    # Example: Predict user ranking (ensure your model expects this format)
    X = df[['performance_metric']]
    df['ranking'] = model.predict(X)
    
    # Sort users by ranking
    ranked_users = df.sort_values(by='ranking', ascending=False)
    return ranked_users

# Example function to reward badges based on performance
def assign_badges():
    ranked_users = rank_users()
    badges = []

    for index, row in ranked_users.iterrows():
        if row['performance_metric'] > 100:  # Example threshold
            badge = {'user_id': row['user_id'], 'badge': 'Gold'}
        elif row['performance_metric'] > 50:
            badge = {'user_id': row['user_id'], 'badge': 'Silver'}
        else:
            badge = {'user_id': row['user_id'], 'badge': 'Bronze'}
        badges.append(badge)
    
    # Insert badges into the database
    conn = get_db_connection()
    cur = conn.cursor()
    for badge in badges:
        cur.execute(
            'INSERT INTO user_badges (user_id, badge) VALUES (%s, %s)',
            (badge['user_id'], badge['badge'])
        )
    conn.commit()
    cur.close()
    conn.close()


app = Flask(__name__)

# Database connection function
def get_db_connection():
    conn = psycopg2.connect(
        dbname='db',  # Your database name
        user='postgres',
        password='09876',
        host='localhost',
        port='5432'
    )
    return conn

# Route for user signup
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()  # Get data from request body
    username = data['username']
    email = data['email']
    password = data['password']

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Check if the user already exists
        cur.execute('SELECT * FROM login WHERE email = %s', (email,))
        user_exists = cur.fetchone()

        if user_exists:
            return jsonify({'message': 'User already exists with this email'}), 400

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Insert new user into the database
        cur.execute(
            'INSERT INTO login (username, email, password) VALUES (%s, %s, %s)',
            (username, email, hashed_password.decode('utf-8'))
        )
        conn.commit()
        return jsonify({'message': 'User registered successfully!'}), 201

    except Exception as e:
        print('Error during signup:', e)
        return jsonify({'message': 'An error occurred during signup'}), 500

    finally:
        cur.close()
        conn.close()

# Route for user login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()  # Get data from request body
    email = data['email']
    password = data['password']

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Retrieve user data from the database
        cur.execute('SELECT * FROM login WHERE email = %s', (email,))
        user = cur.fetchone()

        if not user:
            return jsonify({'message': 'User not found'}), 400

        stored_password = user[2]  # Assuming password is the third column in the table

        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
            return jsonify({'message': 'Invalid email or password'}), 400

        return jsonify({'message': 'Login successful!'}), 200

    except Exception as e:
        print('Error during login:', e)
        return jsonify({'message': 'An error occurred during login'}), 500

    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
