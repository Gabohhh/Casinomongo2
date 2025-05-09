import json
import random
from faker import Faker
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson.objectid import ObjectId
import bcrypt

fake = Faker()

# Game configuration
GAME_TYPES = {
    'Blackjack': {'win_prob': 0.45, 'max_win': 500, 'max_loss': 200},
    'Slots': {'win_prob': 0.35, 'max_win': 1000, 'max_loss': 50},
    'Roulette': {'win_prob': 0.48, 'max_win': 300, 'max_loss': 100},
    'Poker': {'win_prob': 0.40, 'max_win': 800, 'max_loss': 150},
    'Baccarat': {'win_prob': 0.49, 'max_win': 400, 'max_loss': 200}
}

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def generate_game_result(game_type):
    """Generate realistic game results based on game type"""
    config = GAME_TYPES[game_type]
    if random.random() < config['win_prob']:
        amount = round(random.uniform(10, config['max_win']), 2)
    else:
        amount = round(random.uniform(-config['max_loss'], -5), 2)
    return amount

def generate_random_users(num_users):
    """Generate users with initial balances"""
    roles = ['normal'] * 80 + ['vip'] * 15 + ['admin'] * 5
    users = []
    
    for i in range(num_users):
        created_at = fake.date_time_between(start_date='-2y', end_date='now')
        user = {
            "_id": str(ObjectId()),
            "email": fake.unique.email(),
            "password": hash_password("Password123!").decode('utf-8'),
            "role": random.choice(roles),
            "balance": round(random.uniform(100, 10000), 2),  # Starting balance
            "active": random.choices([True, False], weights=[90, 10])[0],
            "created_at": created_at,
            "created_at_str": created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        users.append(user)
    
    return users

def generate_user_transactions(user, num_transactions):
    """Generate transaction history that properly affects user balance"""
    transactions = []
    current_balance = user['balance']
    game_list = list(GAME_TYPES.keys())
    
    # Convert created_at to datetime if it's a string
    if isinstance(user['created_at'], str):
        user['created_at'] = datetime.strptime(user['created_at'], '%Y-%m-%d %H:%M:%S')
    
    for _ in range(num_transactions):
        # Determine transaction type with weighted probabilities
        tx_type = random.choices(
            ['deposit', 'withdrawal', 'game'],
            weights=[20, 15, 65]
        )[0]
        
        if tx_type == 'deposit':
            amount = round(random.uniform(10, 1000), 2)
            current_balance += amount
            game = "N/A"
        elif tx_type == 'withdrawal':
            amount = round(random.uniform(10, min(500, current_balance)), 2) * -1
            current_balance += amount  # Withdrawals are negative
            game = "N/A"
        else:  # game
            game = random.choice(game_list)
            amount = generate_game_result(game)
            current_balance += amount
        
        tx_date = fake.date_time_between(
            start_date=user['created_at'],
            end_date='now'
        )
        
        tx = {
            "user_id": user["_id"],
            "type": tx_type,
            "amount": amount,
            "balance_change": f"+{amount}" if amount >= 0 else f"{amount}",
            "new_balance": round(current_balance, 2),
            "game": game,
            "date": tx_date,
            "date_str": tx_date.strftime('%Y-%m-%d %H:%M:%S')
        }
        transactions.append(tx)
        
        # Ensure balance doesn't go negative (casinos don't allow unlimited credit)
        if current_balance < 0:
            current_balance = 0
    
    # Update user's final balance
    user['balance'] = round(current_balance, 2)
    return transactions

def generate_data(num_users, avg_transactions_per_user):
    """Generate complete dataset with consistent balances"""
    print(f"Generating {num_users} users...")
    users = generate_random_users(num_users)
    
    print(f"Generating ~{num_users * avg_transactions_per_user} transactions...")
    all_transactions = []
    for user in users:
        # Randomize transactions per user (1-3x average)
        num_tx = random.randint(
            max(1, avg_transactions_per_user // 2),
            avg_transactions_per_user * 2
        )
        transactions = generate_user_transactions(user, num_tx)
        all_transactions.extend(transactions)
    
    return users, all_transactions

def save_to_json(data, filename):
    """Save data to JSON file with proper date serialization"""
    def json_serial(obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        raise TypeError("Type not serializable")
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2, default=json_serial)
    print(f"Saved {len(data)} records to {filename}")

if __name__ == '__main__':
    # Configuration
    NUM_USERS = 5000
    AVG_TRANSACTIONS_PER_USER = 4
    USERS_FILE = "C:/Users/Usuario#INF275/Documents/Proyects/randomusers/users.json"
    TRANSACTIONS_FILE = "C:/Users/Usuario#INF275/Documents/Proyects/randomusers/transactions.json"
    
    # Generate data
    users, transactions = generate_data(NUM_USERS, AVG_TRANSACTIONS_PER_USER)
    
    # Save to files
    save_to_json(users, USERS_FILE)
    save_to_json(transactions, TRANSACTIONS_FILE)
    
    print("Data generation complete!")
    print(f"Final stats: {len(users)} users, {len(transactions)} transactions")