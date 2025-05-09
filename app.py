from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os
import bcrypt

app = Flask(__name__)
app.secret_key = os.urandom(24)

# MongoDB Setup
client = MongoClient('mongodb://localhost:27017/')
db = client.casino_db
users = db.users
transactions = db.transactions

# Create indexes
users.create_index('email', unique=True)
transactions.create_index('user_id')

# Custom template filters
def format_currency(value):
    return "${:,.2f}".format(value) if value is not None else "$0.00"

app.jinja_env.filters['format_balance'] = format_currency
app.jinja_env.filters['format_currency'] = format_currency

# Helper Functions
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(hashed_pw, user_pw):
    return bcrypt.checkpw(user_pw.encode('utf-8'), hashed_pw)

def is_admin():
    return 'user' in session and session['user']['role'] == 'admin'

# Routes
@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = users.find_one({'email': request.form['email']})
        if user and check_password(user['password'], request.form['password']):
            session['user'] = {
                'id': str(user['_id']),
                'email': user['email'],
                'role': user['role']
            }
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html', user=None)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_data = users.find_one({'_id': ObjectId(session['user']['id'])})
    return render_template('dashboard.html', 
                         user=user_data,
                         user_count=users.count_documents({}))

@app.route('/admin/users')
def admin_users():
    if not is_admin(): 
        return redirect(url_for('dashboard'))
    return render_template('admin_users.html',
                         users=list(users.find()))

@app.route('/admin/users/add', methods=['GET', 'POST'])
def add_user():
    if not is_admin():
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            users.insert_one({
                'email': request.form['email'],
                'password': hash_password(request.form['password']),
                'role': request.form['role'],
                'balance': float(request.form.get('balance', 0)),
                'active': 'active' in request.form,
                'created_at': datetime.now()
            })
            flash('User added successfully', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            flash(f'Error adding user: {str(e)}', 'danger')
    
    return render_template('add_edit_user.html', user=None)

@app.route('/admin/users/edit/<user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if not is_admin():
        return redirect(url_for('dashboard'))
    
    user = users.find_one({'_id': ObjectId(user_id)})
    
    if request.method == 'POST':
        try:
            update_data = {
                'email': request.form['email'],
                'role': request.form['role'],
                'balance': float(request.form.get('balance', 0)),
                'active': 'active' in request.form
            }
            
            if request.form.get('password'):
                update_data['password'] = hash_password(request.form['password'])
            
            users.update_one({'_id': ObjectId(user_id)}, {'$set': update_data})
            flash('User updated successfully', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            flash(f'Error updating user: {str(e)}', 'danger')
    
    return render_template('add_edit_user.html', user=user)

@app.route('/admin/users/delete/<user_id>')
def delete_user(user_id):
    if not is_admin():
        return redirect(url_for('dashboard'))
    
    try:
        users.delete_one({'_id': ObjectId(user_id)})
        flash('User deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/transactions/<user_id>')
def user_transactions(user_id):
    if not is_admin(): 
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        tx_list = list(transactions.find({'user_id': ObjectId(user_id)}).sort('date', -1))
        return jsonify([{
            'date': tx['date'].strftime('%Y-%m-%d %H:%M'),
            'type': tx['type'],
            'amount': tx['amount'],
            'game': tx.get('game', 'N/A'),
            'balance_change': tx.get('balance_change', 'N/A'),
            'new_balance': tx.get('new_balance', 'N/A')
        } for tx in tx_list])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def create_sample_transactions():
    if transactions.count_documents({}) == 0:
        sample_user = users.find_one({'email': 'admin@casino.com'})
        if sample_user:
            sample_tx = [
                {
                    'user_id': sample_user['_id'],
                    'type': 'deposit',
                    'amount': 1000,
                    'balance_change': '+1000',
                    'new_balance': 1000,
                    'date': datetime.now(),
                    'game': 'N/A'
                },
                {
                    'user_id': sample_user['_id'],
                    'type': 'game',
                    'amount': -200,
                    'balance_change': '-200',
                    'new_balance': 800,
                    'date': datetime.now(),
                    'game': 'Blackjack'
                },
                {
                    'user_id': sample_user['_id'],
                    'type': 'game',
                    'amount': 500,
                    'balance_change': '+500',
                    'new_balance': 1300,
                    'date': datetime.now(),
                    'game': 'Slots'
                }
            ]
            transactions.insert_many(sample_tx)

if __name__ == '__main__':
    # Create admin if not exists
    if not users.find_one({'email': 'admin@casino.com'}):
        users.insert_one({
            'email': 'admin@casino.com',
            'password': hash_password('Admin123!'),
            'role': 'admin',
            'balance': 0,
            'created_at': datetime.now()
        })
    
    create_sample_transactions()
    app.run(debug=True)