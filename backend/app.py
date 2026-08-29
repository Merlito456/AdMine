from flask import Flask, request, jsonify
from flask_cors import CORS
from blockchain_with_supabase import blockchain, TOKEN_SYMBOL
import time

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return jsonify({
        "app": "AdMine Blockchain",
        "token": TOKEN_SYMBOL,
        "status": "running"
    })

@app.route('/api/token-info', methods=['GET'])
def get_token_info():
    return jsonify(blockchain.get_token_info())

@app.route('/api/blockchain', methods=['GET'])
def get_blockchain():
    return jsonify(blockchain.to_dict())

@app.route('/api/stats', methods=['GET'])
def get_stats():
    return jsonify(blockchain.get_blockchain_stats())

@app.route('/api/balance/<address>', methods=['GET'])
def get_balance(address):
    balance = blockchain.get_balance(address)
    return jsonify({
        "address": address,
        "balance": balance,
        "token": TOKEN_SYMBOL
    })

@app.route('/api/wallets/top', methods=['GET'])
def get_top_wallets():
    limit = request.args.get('limit', 10, type=int)
    wallets = blockchain.get_all_wallets(limit)
    return jsonify({"wallets": wallets})

@app.route('/api/mine', methods=['POST'])
def mine_block():
    data = request.json
    address = data.get('address', 'admin_wallet')
    
    block = blockchain.mine_pending_transactions(address)
    if block:
        return jsonify({
            "status": "success",
            "block_index": block.index,
            "block_hash": block.hash,
            "message": f"Block mined! +{blockchain.mining_reward} {TOKEN_SYMBOL}"
        })
    else:
        return jsonify({
            "status": "error",
            "message": "No pending transactions to mine"
        })

@app.route('/api/ad-reward', methods=['POST'])
def process_ad_reward():
    data = request.json
    wallet_address = data.get('wallet_address')
    
    if not wallet_address:
        return jsonify({"error": "Wallet address required"}), 400
    
    # Add reward transaction
    transaction = {
        "from": "ad_system",
        "to": wallet_address,
        "amount": blockchain.ad_reward,
        "type": "ad_reward",
        "token": TOKEN_SYMBOL,
        "timestamp": time.time()
    }
    
    blockchain.add_transaction(transaction)
    
    # Auto-mine if enough transactions
    if len(blockchain.pending_transactions) >= 3:
        blockchain.mine_pending_transactions("system_reward")
    
    return jsonify({
        "status": "success",
        "reward": blockchain.ad_reward,
        "token": TOKEN_SYMBOL,
        "address": wallet_address,
        "new_balance": blockchain.get_balance(wallet_address)
    })

@app.route('/api/wallet/create', methods=['POST'])
def create_wallet():
    import secrets
    import hashlib
    
    # Generate wallet
    private_key = secrets.token_bytes(32).hex()
    public_key = hashlib.sha256(private_key.encode()).hexdigest()
    address = hashlib.sha256(public_key.encode()).hexdigest()[:40]
    
    # Save to Supabase
    try:
        blockchain.update_wallet_balance(address, 0)
        return jsonify({
            "address": address,
            "private_key": private_key,
            "public_key": public_key,
            "balance": 0,
            "token": TOKEN_SYMBOL
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wallet/<address>/transactions', methods=['GET'])
def get_wallet_transactions(address):
    # Get from Supabase
    try:
        from blockchain_with_supabase import supabase
        response = supabase.table('transactions').select('*').or_(
            f'from_address.eq.{address},to_address.eq.{address}'
        ).order('timestamp', desc=True).limit(50).execute()
        return jsonify({
            "address": address,
            "transactions": response.data,
            "count": len(response.data)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/verify-chain', methods=['GET'])
def verify_chain():
    is_valid = blockchain.validate_chain()
    return jsonify({
        "valid": is_valid,
        "chain_length": len(blockchain.chain)
    })

@app.route('/api/initialize', methods=['POST'])
def initialize_blockchain():
    """Initialize blockchain if not already initialized"""
    if len(blockchain.chain) > 1:
        return jsonify({
            "status": "error",
            "message": "Blockchain already initialized"
        })
    
    blockchain.create_genesis_block()
    return jsonify({
        "status": "success",
        "message": "Blockchain initialized with genesis block",
        "block_count": len(blockchain.chain)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
