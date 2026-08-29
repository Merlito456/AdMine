from flask import Flask, request, jsonify
from flask_cors import CORS
from blockchain import blockchain
from wallet import Wallet
import json

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return jsonify({
        "message": "Blockchain Ecosystem API",
        "version": "1.0.0"
    })

@app.route('/api/blockchain', methods=['GET'])
def get_blockchain():
    return jsonify(blockchain.to_dict())

@app.route('/api/balance/<address>', methods=['GET'])
def get_balance(address):
    balance = blockchain.get_balance(address)
    return jsonify({"address": address, "balance": balance})

@app.route('/api/transaction', methods=['POST'])
def create_transaction():
    data = request.json
    required = ['from', 'to', 'amount']
    
    if not all(key in data for key in required):
        return jsonify({"error": "Missing required fields"}), 400
    
    transaction = {
        "from": data['from'],
        "to": data['to'],
        "amount": float(data['amount']),
        "timestamp": __import__('time').time()
    }
    
    blockchain.add_transaction(transaction)
    return jsonify({"status": "success", "transaction": transaction})

@app.route('/api/mine', methods=['POST'])
def mine_block():
    data = request.json
    address = data.get('address')
    
    if not address:
        return jsonify({"error": "Address required"}), 400
    
    blockchain.mine_pending_transactions(address)
    return jsonify({
        "status": "success",
        "message": f"Block mined for {address}"
    })

@app.route('/api/ad-reward', methods=['POST'])
def process_ad_reward():
    data = request.json
    wallet_address = data.get('wallet_address')
    
    if not wallet_address:
        return jsonify({"error": "Wallet address required"}), 400
    
    result = blockchain.get_ad_reward(wallet_address)
    return jsonify(result)

@app.route('/api/wallet/create', methods=['POST'])
def create_wallet():
    wallet = Wallet()
    return jsonify({
        "address": wallet.address,
        "private_key": wallet.private_key.hex() if hasattr(wallet.private_key, 'hex') else str(wallet.private_key),
        "public_key": wallet.public_key.hex() if hasattr(wallet.public_key, 'hex') else str(wallet.public_key)
    })

@app.route('/api/verify-chain', methods=['GET'])
def verify_chain():
    is_valid = blockchain.validate_chain()
    return jsonify({"valid": is_valid})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
