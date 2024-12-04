import logging
from flask import Flask, render_template, redirect, url_for, request, jsonify
import random
import time 
import csv
from flask import send_file

app = Flask(__name__)

# Set up logging
logger = logging.getLogger()
#log = logging.getLogger('werkzeug')
#log.setLevel(logging.Error)  # Ustawienie logowania na ERROR, żeby wyciszyć INFO i DEBUG

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # Log everything from DEBUG level and above
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# File handler
file_handler = logging.FileHandler('auction_system.log')
file_handler.setLevel(logging.DEBUG)  # Log everything from DEBUG level and above
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Add both handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Lista użytkowników
users = ['telekom1', 'telekom2', 'telekom3', 'telekom4']
logged_in_users = {}
auction_data = {
    'round_time': 60,
    'break_time': 30,
    'start_price': 356000,
    'bid_increment': 7120,
    'current_round': 0,
    'status': 'waiting',
    'bids': [],
    'results': [],
    'current_leaders': {block: None for block in ['A', 'B', 'C', 'D', 'E', 'F', 'G']},
    'block_data': {
        'A': {'start_price': 356000, 'bid_increment': 7120},
        'B': {'start_price': 356000, 'bid_increment': 7120},
        'C': {'start_price': 356000, 'bid_increment': 7120},
        'D': {'start_price': 356000, 'bid_increment': 7120},
        'E': {'start_price': 356000, 'bid_increment': 7120},
        'F': {'start_price': 356000, 'bid_increment': 7120},
        'G': {'start_price': 356000, 'bid_increment': 7120}
    }
}

@app.route('/')
def index():
    return render_template('index.html', users=users, logged_in_users=logged_in_users)

@app.route('/login/<username>')
def login(username):
    if username not in users:
        logger.warning(f"Login attempt for non-existent user: {username}")
        return "User does not exist."
    
    logger.info(f"User {username} logged in.")
    logged_in_users[username] = {'bids': 0, 'active': True, 'skips': 2}
    return redirect(url_for('user_panel', username=username))

@app.route('/user/<username>')
def user_panel(username):
        # Check if the user is logged in
    if username not in logged_in_users:
        logger.warning(f"Unauthorized access attempt by user: {username}")
        return redirect(url_for('index'))  # Redirect to the index page
    
    
    if not logged_in_users[username]['active']:
        return "You have been excluded from the auction for not bidding in the first round."
    
    #user_bids = [bid for bid in auction_data['bids'] if bid['user'] == username] # passing bids only made by user
    #user_bids = [bid for bid in auction_data['bids'] ] # passing all bids
    user_bids = [bid for bid in auction_data['bids'] if bid['round'] < auction_data['current_round'] or (bid['user'] == username and bid['round'] == auction_data['current_round'])]
    
    available_bids = 2
    remaining_time = get_remaining_time()  # Calculate remaining time dynamically
    logger.warning(f"remaining_time: {remaining_time}")
    
    return render_template('user.html', 
                           user=username, 
                           auction_data=auction_data, 
                           user_bids=user_bids, 
                           user_data=logged_in_users[username], 
                           available_bids=available_bids,
                           remaining_time=remaining_time
                           )

@app.route('/admin')
def admin():
    logger.info("Rendering admin panel.")
    return render_template('admin.html', auction_data=auction_data, logged_in_users=logged_in_users)

@app.route('/start_auction')
def start_auction():
    logger.info("Starting a new auction.")
    auction_data['current_round'] = 1
    auction_data['status'] = 'running'
    auction_data['bids'] = []
    auction_data['results'] = []
    auction_data['current_leaders'] = {block: None for block in ['A', 'B', 'C', 'D', 'E', 'F', 'G']}
    auction_data['round_start_time'] = time.time()  # Record the start time of the auction round
    # Reset start_price and bid_increment to initial values
    initial_start_price = 356000
    initial_bid_increment = 7120
    for block in auction_data['block_data']:
        auction_data['block_data'][block]['start_price'] = initial_start_price
        auction_data['block_data'][block]['bid_increment'] = initial_bid_increment
    logger.debug(f"Auction data reset: {auction_data}")
    return redirect(url_for('admin'))

@app.route('/place_bid', methods=['POST'])
def place_bid():
    user = request.form['user']
    block = request.form['block']
    amount = auction_data['block_data'][block]['start_price'] + auction_data['block_data'][block]['bid_increment']
    
    if logged_in_users[user]['bids'] < 2:
        auction_data['bids'].append({'user': user, 'block': block, 'amount': amount, 'round': auction_data['current_round']})
        logged_in_users[user]['bids'] += 1
        auction_data['current_leaders'][block] = user
        print(f' auction_data: {auction_data}')
        logger.info(f"User {user} placed a bid of {amount} on block {block}.")
        logger.info(f"User auction_data: {auction_data}'")
    else:
        logger.warning(f"User {user} attempted to place a bid but reached their bid limit.")
    
    return redirect(url_for('user_panel', username=user))

#@app.route('/skip_round/<username>')
#def skip_round(username):
#    if logged_in_users[username]['skips'] > 0:
#        logged_in_users[username]['skips'] -= 1
#        logger.info(f"User {username} skipped the round. Remaining skips: {logged_in_users[username]['skips']}")
#    else:
#        logger.warning(f"User {username} attempted to skip but has no skips left.")
#    
#    return redirect(url_for('user_panel', username=username))

@app.route('/skip_round/<username>')
def skip_round(username):
    # Check if the user has skips remaining
    if logged_in_users[username]['skips'] > 0:
        logged_in_users[username]['skips'] -= 1
        logger.info(f"User {username} skipped the round. Remaining skips: {logged_in_users[username]['skips']}")
        
        # Add a special bid to indicate skipping
        auction_data['bids'].append({
            'user': username,
            'block': 'A',
            'amount': 0,
            'round': auction_data['current_round'],
            'is_success': 'skipped'
        })
    else:
        logger.warning(f"User {username} attempted to skip but has no skips left.")
    
    return redirect(url_for('user_panel', username=username))

@app.route('/end_round')
def end_round():
    auction_data['status'] = 'break'
    auction_data['current_round'] += 1
    logger.info(f"Round {auction_data['current_round']} ended. Determining winners...")
    determine_winners()
    
    # Check if no bids were placed during the last round
    previous_round_bids = [bid for bid in auction_data['bids'] if bid['round'] == auction_data['current_round'] - 1]
    if not previous_round_bids:
        logger.info("No bids were placed during the last round. Ending the auction.")
        auction_data['status'] = 'finished'
        return redirect(url_for('admin'))  # Redirect to the admin panel to show the auction has ended
    
    update_auction_table()
    auction_data['round_start_time'] = time.time()  # Update the round start time for the new round
    logger.info("Round results updated, auction table refreshed.")
    return redirect(url_for('admin'))

def determine_winners():
    results = {}
    # Only consider bids from the previous round
    previous_round_bids = [bid for bid in auction_data['bids'] if bid['round'] == auction_data['current_round'] - 1]
    
    for bid in previous_round_bids:
        bid['is_success'] = "no"
        block = bid['block']
        if block not in results:
            results[block] = []
        results[block].append(bid)
    
    auction_data['results'] = []
    for block, bids in results.items():
        if len(bids) == 0:
            auction_data['current_leaders'][block] = None
        else:
            # Sort bids in descending order of amount
            sorted_bids = sorted(bids, key=lambda x: x['amount'], reverse=True)
            max_amount = sorted_bids[0]['amount']
            highest_bids = [bid for bid in sorted_bids if bid['amount'] == max_amount]
            
            # Handle ties by selecting a random winner
            if len(highest_bids) > 1:
                winner = random.choice(highest_bids)
            else:
                winner = highest_bids[0]
            
            for bid in bids:
                if bid == winner:
                    bid['is_success'] = "yes"
            
            auction_data['results'].append(winner)
            auction_data['current_leaders'][block] = winner['user']


def update_auction_table():
    for result in auction_data['results']:
        block = result['block']
        # Aktualizuj cenę początkową i przyrost dla konkretnego bloku
        auction_data['block_data'][block]['start_price'] = result['amount']
        auction_data['block_data'][block]['bid_increment'] = round(result['amount'] * 0.02) 
        logger.debug(f"Updated auction table for block {block}: Start Price = {auction_data['block_data'][block]['start_price']}, Bid Increment = {auction_data['block_data'][block]['bid_increment']}")

@app.route('/send_results')
def send_results():
    auction_data['status'] = 'running'
    auction_data['round_start_time'] = time.time()  # Record the start time of the auction round
    for user in logged_in_users:
        logged_in_users[user]['bids'] = 0
    logger.info("Auction results sent and auction reset.")
    return redirect(url_for('admin'))

@app.route('/check_status')
def check_status():
    return jsonify(status=auction_data['status'], round=auction_data['current_round'], leaders=auction_data['current_leaders'])

def get_remaining_time():
    logger.debug(f"get_remaining_time - pobieranie round_start_time z auction data: {auction_data.get('round_start_time')}")
    if 'round_start_time' not in auction_data or auction_data['status'] != 'running':
        return 0  # No active round
    elapsed_time = time.time() - auction_data['round_start_time']
    return max(0, auction_data['round_time'] - int(elapsed_time))

@app.route('/export_auction_table')
def export_auction_table():
    # Create a CSV file with the auction table
    csv_file = 'auction_table.csv'
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Block', 'Start Price', 'Winner'])
        for block, data in auction_data['block_data'].items():
            writer.writerow([block, data['start_price'], auction_data['current_leaders'][block]])
    
    return send_file(csv_file, as_attachment=True)

@app.route('/export_my_bids/<username>')
def export_my_bids(username):
    # Create a CSV file with the user's bids
    csv_file = f'{username}_bids.csv'
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Round', 'Block', 'Amount', 'User' ,'Status'])
        for bid in auction_data['bids']:
            writer.writerow([bid['round'], bid['block'], bid['amount'], bid['user'],bid['is_success'] ])
    
    return send_file(csv_file, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=False)