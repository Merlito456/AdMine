from flask import Flask, request, jsonify
from flask_cors import CORS
from blockchain import blockchain, TOKEN_SYMBOL, TOKEN_NAME
from supabase_client import supabase_client
from wallet import Wallet
import json
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return jsonify({
        "app_name": "AdMine Blockchain",
        "token": TOKEN_NAME,
        "symbol": TOKEN_SYMBOL,
        "version": "1.0.0",
        "message": f"Mine {TOKEN_SYMBOL} by watching ads!"
    })

@app.route('/api/token-info', methods=['GET'])
def get_token_info():
    return jsonify(blockchain.get_token_info())

@app.route('/api/blockchain', methods=['GET'])
def get_blockchain():
    return jsonify(blockchain.to_dict())

@app.route('/api/balance/<address>', methods=['GET'])
def get_balance(address):
    balance = blockchain.get_balance(address)
    wallet = supabase_client.get_wallet(address)
    return jsonify({
        "address": address,
        "balance": balance,
        "token": TOKEN_SYMBOL,
        "created_at": wallet['created_at'] if wallet else None,
        "total_earned": supabase_client.get_total_ad_rewards(address)
    })

@app.route('/api/wallet/create', methods=['POST'])
def create_wallet():
    wallet = Wallet()
    
    # Save to Supabase
    supabase_client.create_wallet(
        address=wallet.address,
        private_key=wallet.private_key.hex(),
        public_key=wallet.public_key.hex()
    )
    
    return jsonify({
        "address": wallet.address,
        "private_key": wallet.private_key.hex(),
        "public_key": wallet.public_key.hex(),
        "token": TOKEN_SYMBOL,
        "balance": 0
    })

@app.route('/api/wallet/<address>/transactions', methods=['GET'])
def get_wallet_transactions(address):
    transactions = supabase_client.get_transactions_by_address(address)
    return jsonify({
        "address": address,
        "transactions": transactions,
        "count": len(transactions)
    })

@app.route('/api/wallets/top', methods=['GET'])
def get_top_wallets():
    limit = request.args.get('limit', 10, type=int)
    wallets = supabase_client.get_all_wallets(limit)
    return jsonify({
        "wallets": wallets,
        "count": len(wallets)
    })

@app.route('/api/transaction', methods=['POST'])
def create_transaction():
    data = request.json
    required = ['from', 'to', 'amount']
    
    if not all(key in data for key in required):
        return jsonify({"error": "Missing required fields"}), 400
    
    # Check sender balance
    sender_balance = blockchain.get_balance(data['from'])
    if sender_balance < float(data['amount']):
        return jsonify({"error": "Insufficient balance"}), 400
    
    transaction = {
        "from": data['from'],
        "to": data['to'],
        "amount": float(data['amount']),
        "token": TOKEN_SYMBOL,
        "type": "transfer",
        "timestamp": time.time()
    }
    
    blockchain.add_transaction(transaction)
    return jsonify({
        "status": "success",
        "transaction": transaction,
        "token": TOKEN_SYMBOL
    })

@app.route('/api/mine', methods=['POST'])
def mine_block():
    data = request.json
    address = data.get('address')
    
    if not address:
        return jsonify({"error": "Address required"}), 400
    
    # Check if wallet exists
    wallet = supabase_client.get_wallet(address)
    if not wallet:
        return jsonify({"error": "Wallet not found"}), 404
    
    blockchain.mine_pending_transactions(address)
    return jsonify({
        "status": "success",
        "message": f"Block mined for {address}",
        "reward": blockchain.mining_reward,
        "token": TOKEN_SYMBOL,
        "new_balance": blockchain.get_balance(address)
    })

@app.route('/api/ad-reward', methods=['POST'])
def process_ad_reward():
    data = request.json
    wallet_address = data.get('wallet_address')
    
    if not wallet_address:
        return jsonify({"error": "Wallet address required"}), 400
    
    result = blockchain.get_ad_reward(wallet_address)
    return jsonify(result)

@app.route('/api/verify-chain', methods=['GET'])
def verify_chain():
    is_valid = blockchain.validate_chain()
    return jsonify({
        "valid": is_valid,
        "chain_length": len(blockchain.chain)
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    stats = supabase_client.get_blockchain_stats()
    return jsonify(stats)

@app.route('/api/ad-rewards/<address>', methods=['GET'])
def get_ad_rewards(address):
    rewards = supabase_client.get_ad_rewards_by_address(address)
    total = supabase_client.get_total_ad_rewards(address)
    return jsonify({
        "address": address,
        "total_rewards": total,
        "rewards": rewards,
        "count": len(rewards)
    })

# Real-time subscriptions (optional)
@app.route('/api/subscribe/transactions', methods=['GET'])
def subscribe_transactions():
    # This would use WebSockets or Server-Sent Events
    # For simplicity, we'll return the latest transactions
    transactions = supabase_client.get_pending_transactions()
    return jsonify({
        "type": "transactions",
        "data": transactions
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
