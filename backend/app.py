from flask import Flask, request, jsonify
from flask_cors import CORS
from blockchain_with_supabase import blockchain, TOKEN_SYMBOL
import time
import os
from datetime import datetime

# ============================================
# CREATE APP FIRST! (This must be first)
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
    """Health check endpoint for Render"""
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
        transaction = {
            "from": "ad_system",
            "to": wallet_address,
            "amount": blockchain.ad_reward,
            "type": "ad_reward",
            "token": TOKEN_SYMBOL,
            "timestamp": time.time()
        }
        
        blockchain.add_transaction(transaction)
        
        if len(blockchain.pending_transactions) >= 3:
            blockchain.mine_pending_transactions("system_reward")
        
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
    """Update mining difficulty"""
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

@app.route('/api/config/reward', methods=['POST'])
def update_reward():
    """Update block reward"""
    data = request.json
    reward = data.get('reward')
    
    if not reward:
        return jsonify({"error": "Reward required"}), 400
    
    blockchain.mining_reward = float(reward)
    
    return jsonify({
        "status": "success",
        "reward": reward,
        "message": f"Block reward updated to {reward} {TOKEN_SYMBOL}"
    })

@app.route('/api/config/ad-reward', methods=['POST'])
def update_ad_reward():
    """Update ad reward"""
    data = request.json
    ad_reward = data.get('ad_reward')
    
    if not ad_reward:
        return jsonify({"error": "Ad reward required"}), 400
    
    blockchain.ad_reward = float(ad_reward)
    
    return jsonify({
        "status": "success",
        "ad_reward": ad_reward,
        "message": f"Ad reward updated to {ad_reward} {TOKEN_SYMBOL}"
    })

@app.route('/api/config/token-name', methods=['POST'])
def update_token_name():
    """Update token name"""
    data = request.json
    name = data.get('name')
    
    if not name:
        return jsonify({"error": "Token name required"}), 400
    
    # Update in blockchain config
    blockchain.token_name = name
    
    return jsonify({
        "status": "success",
        "name": name,
        "message": f"Token name updated to {name}"
    })

@app.route('/api/config/token-symbol', methods=['POST'])
def update_token_symbol():
    """Update token symbol"""
    data = request.json
    symbol = data.get('symbol')
    
    if not symbol or len(symbol) > 5:
        return jsonify({"error": "Valid symbol (max 5 chars) required"}), 400
    
    # Update in blockchain config
    blockchain.token_symbol = symbol.upper()
    
    return jsonify({
        "status": "success",
        "symbol": symbol.upper(),
        "message": f"Token symbol updated to {symbol.upper()}"
    })

@app.route('/api/admin/mint', methods=['POST'])
def mint_tokens():
    """Mint new tokens to an address"""
    data = request.json
    address = data.get('address')
    amount = data.get('amount')
    
    if not address or not amount:
        return jsonify({"error": "Address and amount required"}), 400
    
    # Create mint transaction
    transaction = {
        "from": "system",
        "to": address,
        "amount": float(amount),
        "type": "mint",
        "token": TOKEN_SYMBOL,
        "timestamp": time.time()
    }
    
    blockchain.add_transaction(transaction)
    blockchain.mine_pending_transactions("admin_wallet")
    
    return jsonify({
        "status": "success",
        "minted": amount,
        "address": address,
        "new_balance": blockchain.get_balance(address)
    })

@app.route('/api/admin/burn', methods=['POST'])
def burn_tokens():
    """Burn tokens from an address"""
    data = request.json
    address = data.get('address')
    amount = data.get('amount')
    
    if not address or not amount:
        return jsonify({"error": "Address and amount required"}), 400
    
    # Check balance
    balance = blockchain.get_balance(address)
    if balance < float(amount):
        return jsonify({"error": "Insufficient balance"}), 400
    
    # Create burn transaction
    transaction = {
        "from": address,
        "to": "system",
        "amount": float(amount),
        "type": "burn",
        "token": TOKEN_SYMBOL,
        "timestamp": time.time()
    }
    
    blockchain.add_transaction(transaction)
    blockchain.mine_pending_transactions("admin_wallet")
    
    return jsonify({
        "status": "success",
        "burned": amount,
        "address": address,
        "new_balance": blockchain.get_balance(address)
    })

@app.route('/api/admin/send', methods=['POST'])
def admin_send():
    """Send tokens from admin wallet"""
    data = request.json
    to_address = data.get('to')
    amount = data.get('amount')
    note = data.get('note', '')
    
    if not to_address or not amount:
        return jsonify({"error": "Recipient and amount required"}), 400
    
    # Create transaction
    transaction = {
        "from": "admin_wallet",
        "to": to_address,
        "amount": float(amount),
        "type": "admin_send",
        "note": note,
        "token": TOKEN_SYMBOL,
        "timestamp": time.time()
    }
    
    blockchain.add_transaction(transaction)
    blockchain.mine_pending_transactions("admin_wallet")
    
    return jsonify({
        "status": "success",
        "sent": amount,
        "to": to_address,
        "new_balance": blockchain.get_balance(to_address)
    })

@app.route('/api/admin/export', methods=['GET'])
def export_blockchain():
    """Export blockchain data"""
    return jsonify({
        "blockchain": blockchain.to_dict(),
        "stats": blockchain.get_blockchain_stats(),
        "wallets": blockchain.get_all_wallets(),
        "exported_at": datetime.utcnow().isoformat()
    })

@app.route('/api/admin/reset', methods=['POST'])
def reset_blockchain():
    """Reset blockchain (dangerous!)"""
    try:
        # Clear chain
        blockchain.chain = []
        blockchain.pending_transactions = []
        
        # Create new genesis block
        blockchain.create_genesis_block()
        
        return jsonify({
            "status": "success",
            "message": "Blockchain reset successfully",
            "new_block_count": len(blockchain.chain)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# RUN APP
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
