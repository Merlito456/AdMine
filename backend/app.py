from flask import Flask, request, jsonify
from flask_cors import CORS
from blockchain_with_supabase import blockchain, TOKEN_SYMBOL, TOKEN_NAME
from supabase_client import supabase_client
from auth import (
    auth_register, auth_login, auth_logout, 
    require_auth, get_current_user, get_user_profile,
    bind_wallet_to_user, create_wallet_for_user,
    get_user_wallet, auth_check, verify_session,
    generate_jwt
)
from referral import (
    create_referral_code, process_referral, 
    get_referral_stats, get_referral_tree
)
import time
import os
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv

# ============================================
# LOAD ENVIRONMENT VARIABLES
# ============================================
load_dotenv()

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
        
        # Create wallet with auto-generated referral code
        result = blockchain.create_wallet(address, private_key, public_key)
        
        # Get the generated referral code
        wallet = supabase_client.get_wallet(address)
        referral_code = wallet.get('referral_code') if wallet else None
        
        return jsonify({
            "address": address,
            "private_key": private_key,
            "public_key": public_key,
            "balance": 0,
            "token": TOKEN_SYMBOL,
            "referral_code": referral_code  # Auto-generated
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

@app.route('/api/mining/sessions/<address>', methods=['GET'])
def get_mining_sessions(address):
    """Get mining session history"""
    try:
        sessions = supabase_client.get_mining_sessions(address)
        return jsonify({
            "address": address,
            "sessions": sessions,
            "count": len(sessions)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# ACTIVE MINERS ENDPOINTS - NEW!
# ============================================

@app.route('/api/mining/active-count', methods=['GET'])
def get_active_miners_count():
    """Get count of currently active mining sessions"""
    try:
        from blockchain_with_supabase import supabase
        
        # Count active mining sessions
        response = supabase.table('mining_sessions')\
            .select('wallet_address', count='exact')\
            .eq('status', 'active')\
            .execute()
        
        # Count unique active miners
        active_count = len(response.data) if hasattr(response, 'data') else 0
        
        # Also get total active from wallets table
        wallets_response = supabase.table('wallets')\
            .select('address', count='exact')\
            .eq('mining_active', True)\
            .execute()
        
        total_active = len(wallets_response.data) if hasattr(wallets_response, 'data') else 0
        
        return jsonify({
            "active_miners": max(active_count, total_active),
            "active_sessions": active_count,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mining/active-list', methods=['GET'])
def get_active_miners_list():
    """Get list of currently active miners"""
    try:
        from blockchain_with_supabase import supabase
        
        response = supabase.table('wallets')\
            .select('address, mining_started, balance')\
            .eq('mining_active', True)\
            .order('mining_started', desc=True)\
            .limit(100)\
            .execute()
        
        active_miners = []
        for wallet in response.data if hasattr(response, 'data') else []:
            active_miners.append({
                "address": wallet.get('address', ''),
                "mining_started": wallet.get('mining_started'),
                "balance": wallet.get('balance', 0)
            })
        
        return jsonify({
            "active_miners": active_miners,
            "count": len(active_miners),
            "timestamp": datetime.utcnow().isoformat()
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
            "amount": 0.5,
            "type": "ad_reward",
            "token": TOKEN_SYMBOL,
            "timestamp": time.time()
        }
        
        blockchain.add_transaction(transaction)
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

@app.route('/api/config/token-name', methods=['POST'])
def update_token_name():
    data = request.json
    name = data.get('name')
    
    if not name:
        return jsonify({"error": "Token name required"}), 400
    
    blockchain.token_name = name
    
    return jsonify({
        "status": "success",
        "name": name,
        "message": f"Token name updated to {name}"
    })

@app.route('/api/config/token-symbol', methods=['POST'])
def update_token_symbol():
    data = request.json
    symbol = data.get('symbol')
    
    if not symbol or len(symbol) > 5:
        return jsonify({"error": "Valid symbol (max 5 chars) required"}), 400
    
    blockchain.token_symbol = symbol.upper()
    
    return jsonify({
        "status": "success",
        "symbol": symbol.upper(),
        "message": f"Token symbol updated to {symbol.upper()}"
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

@app.route('/api/admin/send', methods=['POST'])
def admin_send():
    data = request.json
    to_address = data.get('to')
    amount = data.get('amount')
    note = data.get('note', '')
    
    if not to_address or not amount:
        return jsonify({"error": "Recipient and amount required"}), 400
    
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
    blockchain.update_wallet_balance(to_address, float(amount))
    
    return jsonify({
        "status": "success",
        "sent": amount,
        "to": to_address,
        "new_balance": blockchain.get_balance(to_address)
    })

@app.route('/api/admin/export', methods=['GET'])
def export_blockchain():
    return jsonify({
        "blockchain": blockchain.to_dict(),
        "stats": blockchain.get_blockchain_stats(),
        "wallets": blockchain.get_all_wallets(),
        "exported_at": datetime.utcnow().isoformat()
    })

@app.route('/api/admin/reset', methods=['POST'])
def reset_blockchain():
    try:
        blockchain.chain = []
        blockchain.pending_transactions = []
        blockchain.create_genesis_block()
        
        return jsonify({
            "status": "success",
            "message": "Blockchain reset successfully",
            "new_block_count": len(blockchain.chain)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# AUTHENTICATION ROUTES
# ============================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user with auto-generated referral code"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    username = data.get('username')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    result, status = auth_register(email, password, username)
    
    # Add referral code to response if available
    if status == 201 and result.get('user'):
        # Get user's referral code from the result
        if result['user'].get('referral_code'):
            # Already included in auth_register response
            pass
    
    return jsonify(result), status

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    result, status = auth_login(email, password)
    return jsonify(result), status

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Logout user"""
    result, status = auth_logout()
    return jsonify(result), status

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Check authentication status"""
    result, status = auth_check()
    return jsonify(result), status

@app.route('/api/auth/profile', methods=['GET'])
@require_auth
def profile():
    """Get user profile"""
    user = get_current_user()
    result, status = get_user_profile(user['user_id'])
    return jsonify(result), status

@app.route('/api/auth/wallet/create', methods=['POST'])
@require_auth
def create_user_wallet():
    """Create a wallet for the current user with auto-generated referral code"""
    user = get_current_user()
    result, status = create_wallet_for_user(user['user_id'])
    return jsonify(result), status

@app.route('/api/auth/wallet/bind', methods=['POST'])
@require_auth
def bind_wallet():
    """Bind an existing wallet to the current user"""
    user = get_current_user()
    data = request.json
    
    address = data.get('address')
    private_key = data.get('private_key')
    public_key = data.get('public_key')
    
    if not address or not private_key or not public_key:
        return jsonify({'error': 'Wallet details required'}), 400
    
    result, status = bind_wallet_to_user(user['user_id'], address, private_key, public_key)
    return jsonify(result), status

@app.route('/api/auth/wallet', methods=['GET'])
@require_auth
def get_wallet():
    """Get user's wallet"""
    user = get_current_user()
    result, status = get_user_wallet(user['user_id'])
    if status == 200:
        return jsonify({'status': 'success', 'wallet': result}), 200
    return jsonify({'error': result.get('error', 'Wallet not found')}), status

@app.route('/api/auth/refresh', methods=['POST'])
@require_auth
def refresh_token():
    """Refresh JWT token"""
    user = get_current_user()
    token = generate_jwt(user['user_id'], user['email'])
    return jsonify({'token': token}), 200

# ============================================
# REFERRAL ROUTES
# ============================================

@app.route('/api/referral/code', methods=['POST'])
def generate_referral_code():
    """Generate a referral code for a wallet"""
    try:
        data = request.json
        address = data.get('address')
        
        if not address:
            return jsonify({"error": "Wallet address required"}), 400
        
        result, status = create_referral_code(address)
        return jsonify(result), status
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/referral/process', methods=['POST'])
def process_referral_route():
    """Process a new referral"""
    try:
        data = request.json
        referrer_code = data.get('referrer_code')
        new_address = data.get('new_address')
        
        if not referrer_code or not new_address:
            return jsonify({"error": "Referrer code and new address required"}), 400
        
        result, status = process_referral(referrer_code, new_address)
        return jsonify(result), status
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/referral/stats/<address>', methods=['GET'])
def get_referral_stats_route(address):
    """Get referral statistics for a wallet"""
    try:
        stats = get_referral_stats(address)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/referral/tree/<address>', methods=['GET'])
def get_referral_tree_route(address):
    """Get referral tree for a wallet"""
    try:
        depth = request.args.get('depth', 3, type=int)
        tree = get_referral_tree(address, depth)
        return jsonify({"address": address, "tree": tree})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/referral/rewards/<address>', methods=['GET'])
def get_referral_rewards(address):
    """Get referral rewards for a wallet"""
    try:
        rewards = supabase_client.get_referral_rewards(address)
        return jsonify({"address": address, "rewards": rewards, "count": len(rewards)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# GAME REWARD SYSTEM
# ============================================

@app.route('/api/games/reward', methods=['POST'])
def claim_game_reward():
    """Claim reward from a game and update database directly"""
    try:
        data = request.json
        wallet_address = data.get('wallet_address')
        game_name = data.get('game_name')
        reward_amount = data.get('reward_amount', 0)
        game_score = data.get('game_score', 0)
        game_session = data.get('game_session', None)
        
        if not wallet_address or not game_name:
            return jsonify({"error": "Wallet address and game name required"}), 400
        
        if reward_amount <= 0:
            return jsonify({"error": "Reward amount must be greater than 0"}), 400
        
        # 1. Check if wallet exists
        wallet = supabase_client.get_wallet(wallet_address)
        if not wallet:
            return jsonify({"error": "Wallet not found"}), 404
        
        # 2. Update wallet balance
        current_balance = wallet.get('balance', 0)
        new_balance = current_balance + reward_amount
        supabase_client.update_balance(wallet_address, new_balance)
        
        # 3. Update game stats in wallet
        supabase_client.update_wallet_stats(
            wallet_address,
            total_games_played=1,
            total_games_won=1 if game_score > 0 else 0,
            total_game_rewards=reward_amount,
            last_game_played=datetime.now(timezone.utc).isoformat()
        )
        
        # 4. Record game history
        game_record = {
            'wallet_address': wallet_address,
            'game_name': game_name,
            'reward_amount': reward_amount,
            'game_score': game_score,
            'game_session': game_session or str(uuid.uuid4()),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        supabase_client.save_game_history(game_record)
        
        # 5. Create blockchain transaction for transparency
        transaction = {
            "from": "game_system",
            "to": wallet_address,
            "amount": reward_amount,
            "type": "game_reward",
            "token": TOKEN_SYMBOL,
            "timestamp": time.time(),
            "game_name": game_name,
            "game_score": game_score
        }
        blockchain.add_transaction(transaction)
        
        # 6. Update total supply
        blockchain.total_supply += reward_amount
        blockchain.circulating_supply += reward_amount
        
        return jsonify({
            "status": "success",
            "message": f"Earned {reward_amount} {TOKEN_SYMBOL} from {game_name}!",
            "reward": reward_amount,
            "token": TOKEN_SYMBOL,
            "address": wallet_address,
            "new_balance": new_balance,
            "game_name": game_name,
            "game_score": game_score,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/games/history/<address>', methods=['GET'])
def get_game_history(address):
    """Get game history for a wallet"""
    try:
        history = supabase_client.get_game_history(address, limit=50)
        return jsonify({
            "address": address,
            "history": history,
            "count": len(history)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/games/stats/<address>', methods=['GET'])
def get_game_stats(address):
    """Get game statistics for a wallet"""
    try:
        stats = supabase_client.get_game_stats(address)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/games/leaderboard', methods=['GET'])
def get_game_leaderboard():
    """Get global game leaderboard"""
    try:
        limit = request.args.get('limit', 20, type=int)
        game = request.args.get('game', None)
        
        if game:
            leaderboard = supabase_client.get_game_leaderboard(game, limit)
        else:
            leaderboard = supabase_client.get_game_leaderboard_all(limit)
            
        return jsonify({
            "leaderboard": leaderboard,
            "count": len(leaderboard)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# ANDROID APP SPECIFIC ENDPOINTS
# ============================================

# --------------------------------
# AD REWARD TRACKING
# --------------------------------

@app.route('/api/ad/watch', methods=['POST'])
def track_ad_watch():
    """Track ad viewing and reward user"""
    try:
        data = request.json
        wallet_address = data.get('wallet_address')
        ad_type = data.get('ad_type', 'rewarded')
        ad_unit_id = data.get('ad_unit_id', '')
        watch_duration = data.get('duration', 0)
        
        if not wallet_address:
            return jsonify({"error": "Wallet address required"}), 400
        
        # Get reward amount based on ad type
        reward_amounts = {
            'rewarded': 0.5,
            'rewarded_interstitial': 1.0,
            'banner': 0.1,
            'native': 0.2,
            'app_open': 0.3
        }
        reward = reward_amounts.get(ad_type, 0.5)
        
        # Record ad watch
        ad_record = {
            'wallet_address': wallet_address,
            'ad_type': ad_type,
            'ad_unit_id': ad_unit_id,
            'reward_amount': reward,
            'reward_claimed': True,
            'watch_duration': watch_duration,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        from blockchain_with_supabase import supabase
        supabase.table('ad_watch_history').insert(ad_record).execute()
        
        # Update wallet stats
        wallet = supabase.table('wallets').select('total_ads_watched, total_ad_rewards').eq('address', wallet_address).execute()
        if wallet.data:
            current_ads = wallet.data[0].get('total_ads_watched', 0)
            current_rewards = wallet.data[0].get('total_ad_rewards', 0)
            
            supabase.table('wallets').update({
                'total_ads_watched': current_ads + 1,
                'total_ad_rewards': float(current_rewards) + reward,
                'last_ad_watch': datetime.now(timezone.utc).isoformat()
            }).eq('address', wallet_address).execute()
        
        # Create reward transaction
        transaction = {
            "from": "ad_system",
            "to": wallet_address,
            "amount": reward,
            "type": "ad_reward",
            "token": TOKEN_SYMBOL,
            "timestamp": time.time()
        }
        blockchain.add_transaction(transaction)
        blockchain.update_wallet_balance(wallet_address, reward)
        
        return jsonify({
            "status": "success",
            "reward": reward,
            "token": TOKEN_SYMBOL,
            "address": wallet_address,
            "new_balance": blockchain.get_balance(wallet_address),
            "message": f"Earned {reward} {TOKEN_SYMBOL} from ad!"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ad/history/<address>', methods=['GET'])
def get_ad_history(address):
    """Get ad watching history for a user"""
    try:
        from blockchain_with_supabase import supabase
        response = supabase.table('ad_watch_history')\
            .select('*')\
            .eq('wallet_address', address)\
            .order('timestamp', desc=True)\
            .limit(50)\
            .execute()
        
        return jsonify({
            "address": address,
            "history": response.data,
            "count": len(response.data)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ad/stats', methods=['GET'])
def get_ad_stats():
    """Get global ad statistics"""
    try:
        from blockchain_with_supabase import supabase
        
        views_resp = supabase.table('ad_watch_history').select('*', count='exact').execute()
        total_views = len(views_resp.data) if hasattr(views_resp, 'data') else 0
        
        rewards_resp = supabase.table('ad_watch_history')\
            .select('reward_amount')\
            .execute()
        total_rewards = sum([r['reward_amount'] for r in rewards_resp.data]) if hasattr(rewards_resp, 'data') else 0
        
        return jsonify({
            "total_ad_views": total_views,
            "total_ad_rewards": total_rewards,
            "token": TOKEN_SYMBOL
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --------------------------------
# USER ANALYTICS (ONLY ONE VERSION)
# --------------------------------

@app.route('/api/analytics/track', methods=['POST'])
def track_analytics():
    """Track user analytics from app"""
    try:
        data = request.json
        wallet_address = data.get('wallet_address')
        session_id = data.get('session_id', str(uuid.uuid4()))
        screen_name = data.get('screen', 'unknown')
        action_type = data.get('action', 'view')
        action_data = data.get('data', {})
        
        if not wallet_address:
            return jsonify({"error": "Wallet address required"}), 400
        
        from blockchain_with_supabase import supabase
        record = {
            'wallet_address': wallet_address,
            'session_id': session_id,
            'screen_name': screen_name,
            'action_type': action_type,
            'action_data': action_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        supabase.table('app_analytics').insert(record).execute()
        
        supabase.table('wallets').update({
            'last_active': datetime.now(timezone.utc).isoformat()
        }).eq('address', wallet_address).execute()
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/user/<address>', methods=['GET'])
def get_user_analytics(address):
    """Get user analytics data"""
    try:
        from blockchain_with_supabase import supabase
        
        stats_resp = supabase.table('user_stats').select('*').eq('address', address).execute()
        
        activity_resp = supabase.table('app_analytics')\
            .select('*')\
            .eq('wallet_address', address)\
            .order('timestamp', desc=True)\
            .limit(20)\
            .execute()
        
        return jsonify({
            "address": address,
            "stats": stats_resp.data[0] if stats_resp.data else {},
            "recent_activity": activity_resp.data,
            "token": TOKEN_SYMBOL
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --------------------------------
# USER DASHBOARD / STATS
# --------------------------------

@app.route('/api/user/dashboard/<address>', methods=['GET'])
def get_user_dashboard(address):
    """Get complete user dashboard data"""
    try:
        from blockchain_with_supabase import supabase
        
        wallet_resp = supabase.table('wallets').select('*').eq('address', address).execute()
        wallet = wallet_resp.data[0] if wallet_resp.data else None
        
        if not wallet:
            return jsonify({"error": "Wallet not found"}), 404
        
        ad_resp = supabase.table('ad_watch_history')\
            .select('*')\
            .eq('wallet_address', address)\
            .order('timestamp', desc=True)\
            .limit(10)\
            .execute()
        
        mining_resp = supabase.table('mining_sessions')\
            .select('*')\
            .eq('wallet_address', address)\
            .order('start_time', desc=True)\
            .limit(10)\
            .execute()
        
        mining_status = blockchain.get_mining_status(address)
        
        return jsonify({
            "address": address,
            "balance": wallet.get('balance', 0),
            "token": TOKEN_SYMBOL,
            "stats": {
                "total_ads_watched": wallet.get('total_ads_watched', 0),
                "total_ad_rewards": float(wallet.get('total_ad_rewards', 0)),
                "total_mining_sessions": wallet.get('total_mining_sessions', 0),
                "last_active": wallet.get('last_active'),
                "mining_active": mining_status.get('status') == 'active' if not mining_status.get('error') else False
            },
            "recent_ads": ad_resp.data if hasattr(ad_resp, 'data') else [],
            "recent_mining": mining_resp.data if hasattr(mining_resp, 'data') else [],
            "mining_status": mining_status
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/stats/<address>', methods=['GET'])
def get_user_stats(address):
    try:
        stats = supabase_client.get_user_stats(address)
        if stats:
            return jsonify(stats)
        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --------------------------------
# APP CONFIGURATION
# --------------------------------

@app.route('/api/app/config', methods=['GET'])
def get_app_config():
    """Get app configuration for Android app"""
    return jsonify({
        "app_name": "AdMine",
        "token_symbol": TOKEN_SYMBOL,
        "token_name": TOKEN_NAME,
        "mining_rate": blockchain.hourly_rate,
        "daily_cap": blockchain.daily_cap,
        "claim_interval": blockchain.claim_interval_hours,
        "ad_rewards": {
            "rewarded": 0.5,
            "rewarded_interstitial": 1.0,
            "banner": 0.1,
            "native": 0.2,
            "app_open": 0.3
        },
        "version": "1.0.0",
        "api_version": "v1"
    })

# ============================================
# RUN APP
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
