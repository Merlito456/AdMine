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
    
    # Update in memory and database
    blockchain.difficulty = int(difficulty)
    
    # Save to Supabase config table
    try:
        from blockchain_with_supabase import supabase
        supabase.table('config').upsert({
            'key': 'difficulty',
            'value': difficulty,
            'updated_at': datetime.utcnow().isoformat()
        }).execute()
    except:
        pass
    
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
