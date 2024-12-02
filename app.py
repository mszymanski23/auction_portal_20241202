from flask import Flask, render_template, redirect, url_for, request, jsonify
import random

app = Flask(__name__)

# Lista użytkowników
users = ['telekom1', 'telekom2', 'telekom3', 'telekom4']
logged_in_users = {}
auction_data = {
    'round_time': 60,
    'break_time': 30,
    'start_price': 10,
    'bid_increment': 10,
    'current_round': 0,
    'status': 'waiting',
    'bids': [],
    'results': [],
    'current_leaders': {block: None for block in ['A', 'B', 'C', 'D', 'E', 'F', 'G']}
}

@app.route('/')
def index():
    return render_template('index.html', users=users, logged_in_users=logged_in_users)

@app.route('/login/<username>')
def login(username):
    logged_in_users[username] = {'bids': 0, 'active': True, 'skips': 2}
    return redirect(url_for('user_panel', username=username))

@app.route('/user/<username>')
def user_panel(username):
    if not logged_in_users[username]['active']:
        return "You have been excluded from the auction for not bidding in the first round."
    user_bids = [bid for bid in auction_data['bids'] if bid['user'] == username]
    return render_template('user.html', user=username, auction_data=auction_data, user_bids=user_bids, user_data=logged_in_users[username])

@app.route('/admin')
def admin():
    return render_template('admin.html', auction_data=auction_data, logged_in_users=logged_in_users)

@app.route('/start_auction')
def start_auction():
    auction_data['current_round'] = 1
    auction_data['status'] = 'running'
    auction_data['bids'] = []
    auction_data['results'] = []
    auction_data['current_leaders'] = {block: None for block in ['A', 'B', 'C', 'D', 'E', 'F', 'G']}
    return redirect(url_for('admin'))

@app.route('/place_bid', methods=['POST'])
def place_bid():
    user = request.form['user']
    block = request.form['block']
    amount = auction_data['start_price'] + auction_data['bid_increment']
    if logged_in_users[user]['bids'] < 2:
        auction_data['bids'].append({'user': user, 'block': block, 'amount': amount, 'round': auction_data['current_round']})
        logged_in_users[user]['bids'] += 1
        auction_data['current_leaders'][block] = user
    return redirect(url_for('user_panel', username=user))

@app.route('/skip_round/<username>')
def skip_round(username):
    if logged_in_users[username]['skips'] > 0:
        logged_in_users[username]['skips'] -= 1
    return redirect(url_for('user_panel', username=username))

@app.route('/end_round')
def end_round():
    auction_data['status'] = 'break'
    auction_data['current_round'] += 1
    determine_winners()
    update_auction_table()
    return redirect(url_for('admin'))

def determine_winners():
    results = {}
    for bid in auction_data['bids']:
        block = bid['block']
        if block not in results:
            results[block] = []
        results[block].append(bid)
    
    for block, bids in results.items():
        if len(bids) > 1:
            winner = random.choice(bids)
        else:
            winner = bids[0]
        auction_data['results'].append(winner)
        auction_data['current_leaders'][block] = winner['user']

def update_auction_table():
    for result in auction_data['results']:
        block = result['block']
        auction_data['start_price'] = result['amount']
        auction_data['bid_increment'] = result['amount'] * 0.1

@app.route('/send_results')
def send_results():
    auction_data['status'] = 'running'
    auction_data['bids'] = []
    for user in logged_in_users:
        logged_in_users[user]['bids'] = 0
    return redirect(url_for('admin'))

@app.route('/check_status')
def check_status():
    return jsonify(status=auction_data['status'], round=auction_data['current_round'], leaders=auction_data['current_leaders'])

if __name__ == '__main__':
    app.run(debug=True)