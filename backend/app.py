from flask import Flask, request, jsonify
from flask_cors import CORS
from blockchain_with_supabase import blockchain, TOKEN_SYMBOL
import time
import os
from datetime import datetime

# ============================================
# CREATE APP
# ============================================
app = Flask(__name__)
CORS(app)

# ============================================
# BASIC ROUTES
# ============================================

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
    try:
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
        private_key = secrets.token_bytes(32).hex()
        public_key = hashlib.sha256(private_key.encode()).hexdigest()
        address = hashlib.sha256(public_key.encode()).hexdigest()[:40]
        
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

# ============================================
# TIME-BASED MINING ROUTES
# ============================================

@app.route('/api/mining/start', methods=['POST'])
def start_mining():
    """Start mining for a wallet"""
    try:
        data = request.json
        address = data.get('address')
        
        if not address:
            return jsonify({"error": "Wallet address required"}), 400
        
        result = blockchain.start_mining(address)
        if result.get('error'):
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mining/stop', methods=['POST'])
def stop_mining():
    """Stop mining and claim rewards"""
    try:
        data = request.json
        address = data.get('address')
        
        if not address:
            return jsonify({"error": "Wallet address required"}), 400
        
        result = blockchain.stop_mining(address)
        if result.get('error'):
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mining/status/<address>', methods=['GET'])
def get_mining_status(address):
    """Get mining status for a wallet"""
    try:
        result = blockchain.get_mining_status(address)
        if result.get('error'):
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mining/claim', methods=['POST'])
def claim_mining_reward():
    """Claim daily mining reward"""
    try:
        data = request.json
        address = data.get('address')
        
        if not address:
            return jsonify({"error": "Wallet address required"}), 400
        
        result = blockchain.claim_daily_reward(address)
        if result.get('error'):
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mining/stats/<address>', methods=['GET'])
def get_mining_stats(address):
    """Get mining statistics for a wallet"""
    try:
        result = blockchain.get_mining_stats(address)
        if result.get('error'):
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mining/config', methods=['POST'])
def update_mining_config():
    """Update mining configuration (Admin only)"""
    try:
        data = request.json
        hourly_rate = data.get('hourly_rate')
        daily_cap = data.get('daily_cap')
        claim_interval = data.get('claim_interval_hours')
        
        result = blockchain.update_mining_config(hourly_rate, daily_cap, claim_interval)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mining/rate', methods=['GET'])
def get_mining_rate():
    """Get current mining rate"""
    try:
        return jsonify({
            "hourly_rate": blockchain.hourly_rate,
            "daily_cap": blockchain.daily_cap,
            "claim_interval_hours": blockchain.claim_interval_hours,
            "token": TOKEN_SYMBOL
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# DEPRECATED BLOCK MINING (Keep for compatibility)
# ============================================

@app.route('/api/mine', methods=['POST'])
def mine_block():
    """Deprecated: Use /api/mining/ instead"""
    return jsonify({
        "status": "deprecated",
        "message": "Block mining is deprecated. Use time-based mining instead.",
        "new_endpoints": {
            "start": "/api/mining/start",
            "stop": "/api/mining/stop",
            "status": "/api/mining/status/{address}",
            "claim": "/api/mining/claim",
            "stats": "/api/mining/stats/{address}"
        }
    })

@app.route('/api/ad-reward', methods=['POST'])
def process_ad_reward():
    data = request.json
    wallet_address = data.get('wallet_address')
    
    if not wallet_address:
        return jsonify({"error": "Wallet address required"}), 400
    
    try:
        transaction = {
            "from": "ad_system",
            "to": wallet_address,
            "amount": 0.5,  # Fixed ad reward
            "type": "ad_reward",
            "token": TOKEN_SYMBOL,
            "timestamp": time.time()
        }
        
        blockchain.add_transaction(transaction)
        
        # Auto-claim mining reward (optional)
        new_balance = blockchain.get_balance(wallet_address)
        
        return jsonify({
            "status": "success",
            "reward": 0.5,
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

# ============================================
# ADMIN CONFIGURATION ROUTES
# ============================================

@app.route('/api/config/difficulty', methods=['POST'])
def update_difficulty():
    data = request.json
    difficulty = data.get('difficulty')
    
    if not difficulty:
        return jsonify({"error": "Difficulty required"}), 400
    
    blockchain.difficulty = int(difficulty)
    
    return jsonify({
        "status": "success",
        "difficulty": difficulty,
        "message": f"Difficulty updated to {difficulty}"
    })

@app.route('/api/admin/mint', methods=['POST'])
def mint_tokens():
    data = request.json
    address = data.get('address')
    amount = data.get('amount')
    
    if not address or not amount:
        return jsonify({"error": "Address and amount required"}), 400
    
    transaction = {
        "from": "system",
        "to": address,
        "amount": float(amount),
        "type": "mint",
        "token": TOKEN_SYMBOL,
        "timestamp": time.time()
    }
    
    blockchain.add_transaction(transaction)
    blockchain.update_wallet_balance(address, float(amount))
    
    return jsonify({
        "status": "success",
        "minted": amount,
        "address": address,
        "new_balance": blockchain.get_balance(address)
    })

@app.route('/api/admin/burn', methods=['POST'])
def burn_tokens():
    data = request.json
    address = data.get('address')
    amount = data.get('amount')
    
    if not address or not amount:
        return jsonify({"error": "Address and amount required"}), 400
    
    balance = blockchain.get_balance(address)
    if balance < float(amount):
        return jsonify({"error": "Insufficient balance"}), 400
    
    transaction = {
        "from": address,
        "to": "system",
        "amount": float(amount),
        "type": "burn",
        "token": TOKEN_SYMBOL,
        "timestamp": time.time()
    }
    
    blockchain.add_transaction(transaction)
    blockchain.update_wallet_balance(address, -float(amount))
    
    return jsonify({
        "status": "success",
        "burned": amount,
        "address": address,
        "new_balance": blockchain.get_balance(address)
    })

# ============================================
# RUN APP
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
