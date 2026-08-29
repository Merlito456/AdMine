# ============================================
# TIME-BASED MINING ROUTES
# ============================================

@app.route('/api/mining/start', methods=['POST'])
def start_mining():
    """Start mining for a wallet"""
    data = request.json
    address = data.get('address')
    
    if not address:
        return jsonify({"error": "Wallet address required"}), 400
    
    result = blockchain.start_mining(address)
    if result.get('error'):
        return jsonify(result), 400
    
    return jsonify(result)

@app.route('/api/mining/stop', methods=['POST'])
def stop_mining():
    """Stop mining and claim rewards"""
    data = request.json
    address = data.get('address')
    
    if not address:
        return jsonify({"error": "Wallet address required"}), 400
    
    result = blockchain.stop_mining(address)
    if result.get('error'):
        return jsonify(result), 400
    
    return jsonify(result)

@app.route('/api/mining/status/<address>', methods=['GET'])
def get_mining_status(address):
    """Get mining status for a wallet"""
    result = blockchain.get_mining_status(address)
    if result.get('error'):
        return jsonify(result), 400
    
    return jsonify(result)

@app.route('/api/mining/claim', methods=['POST'])
def claim_mining_reward():
    """Claim daily mining reward"""
    data = request.json
    address = data.get('address')
    
    if not address:
        return jsonify({"error": "Wallet address required"}), 400
    
    result = blockchain.claim_daily_reward(address)
    if result.get('error'):
        return jsonify(result), 400
    
    return jsonify(result)

@app.route('/api/mining/stats/<address>', methods=['GET'])
def get_mining_stats(address):
    """Get mining statistics for a wallet"""
    result = blockchain.get_mining_stats(address)
    if result.get('error'):
        return jsonify(result), 400
    
    return jsonify(result)

@app.route('/api/mining/config', methods=['POST'])
def update_mining_config():
    """Update mining configuration (Admin only)"""
    data = request.json
    hourly_rate = data.get('hourly_rate')
    daily_cap = data.get('daily_cap')
    claim_interval = data.get('claim_interval_hours')
    
    result = blockchain.update_mining_config(hourly_rate, daily_cap, claim_interval)
    return jsonify(result)
