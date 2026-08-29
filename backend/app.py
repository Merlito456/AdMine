from flask import Flask, request, jsonify
from flask_cors import CORS
from blockchain_with_supabase import blockchain, TOKEN_SYMBOL
import time
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return jsonify({
        "app": "AdMine Blockchain",
        "token": TOKEN_SYMBOL,
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Render"""
    try:
        # Check Supabase connection
        from blockchain_with_supabase import supabase
        supabase.table('blocks').select('count', count='exact').execute()
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 503

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

@app.route('/api/wallet/create', methods=['POST'])
def create_wallet():
    import secrets
    import hashlib
    
    try:
        # Generate wallet
        private_key = secrets.token_bytes(32).hex()
        public_key = hashlib.sha256(private_key.encode()).hexdigest()
        address = hashlib.sha256(public_key.encode()).hexdigest()[:40]
        
        # Create in Supabase
        blockchain.create_wallet(address, private_key, public_key)
        
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

@app.route('/api/mine', methods=['POST'])
def mine_block():
    data = request.json
    address = data.get('address', 'admin_wallet')
    
    try:
        block = blockchain.mine_pending_transactions(address)
        if block:
            return jsonify({
                "status": "success",
                "block_index": block.index,
                "block_hash": block.hash,
                "reward": blockchain.mining_reward,
                "token": TOKEN_SYMBOL,
                "message": f"Block mined! +{blockchain.mining_reward} {TOKEN_SYMBOL}"
            })
        else:
            return jsonify({
                "status": "info",
                "message": "No pending transactions to mine"
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ad-reward', methods=['POST'])
def process_ad_reward():
    data = request.json
    wallet_address = data.get('wallet_address')
    
    if not wallet_address:
        return jsonify({"error": "Wallet address required"}), 400
    
    try:
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
        
        # Get updated balance
        new_balance = blockchain.get_balance(wallet_address)
        
        return jsonify({
            "status": "success",
            "reward": blockchain.ad_reward,
            "token": TOKEN_SYMBOL,
            "address": wallet_address,
            "new_balance": new_balance
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/verify-chain', methods=['GET'])
def verify_chain():
    try:
        is_valid = blockchain.validate_chain()
        return jsonify({
            "valid": is_valid,
            "chain_length": len(blockchain.chain)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/initialize', methods=['POST'])
def initialize_blockchain():
    """Initialize blockchain if not already initialized"""
    try:
        if len(blockchain.chain) > 1:
            return jsonify({
                "status": "info",
                "message": "Blockchain already initialized",
                "block_count": len(blockchain.chain)
            })
        
        blockchain.create_genesis_block()
        return jsonify({
            "status": "success",
            "message": "Blockchain initialized with genesis block",
            "block_count": len(blockchain.chain)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
