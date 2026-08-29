import hashlib
import json
import time
import os
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# ============================================
# SUPABASE CONFIGURATION
# ============================================
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://mydbvqyxoxqzluslpavh.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'sb_publishable_7An_A_PQbrrTzpyrSKOEgw_dPf5mj_o')

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================
# TOKEN CONFIG
# ============================================
TOKEN_SYMBOL = "ADT"
TOKEN_NAME = "Ad Token"
TOKEN_DECIMALS = 18
TOTAL_SUPPLY = 100_000_000

# ============================================
# BLOCKCHAIN CLASS
# ============================================
class Block:
    def __init__(self, index, transactions, timestamp, previous_hash, nonce=0):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "transactions": self.transactions,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty):
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
        return self.hash

    def to_dict(self):
        return {
            "index": self.index,
            "transactions": self.transactions,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
            "nonce": self.nonce
        }

class Blockchain:
    def __init__(self):
        self.difficulty = 4
        self.mining_reward = 10
        self.ad_reward = 0.5
        self.chain = []
        self.pending_transactions = []
        
        # Load from Supabase or create genesis
        self.load_from_db()
    
    def load_from_db(self):
        """Load blockchain from Supabase"""
        try:
            # Get all blocks
            response = supabase.table('blocks').select('*').order('index', desc=False).execute()
            blocks = response.data
            
            if blocks:
                for block_data in blocks:
                    block = Block(
                        index=block_data['index'],
                        transactions=json.loads(block_data['transactions']),
                        timestamp=block_data['timestamp'],
                        previous_hash=block_data['previous_hash'],
                        nonce=block_data['nonce']
                    )
                    block.hash = block_data['hash']
                    self.chain.append(block)
                
                # Load pending transactions
                pending_resp = supabase.table('transactions').select('*').is_('block_index', 'null').execute()
                self.pending_transactions = [json.loads(tx['data']) for tx in pending_resp.data]
                
                print(f"✅ Loaded {len(self.chain)} blocks from Supabase")
            else:
                self.create_genesis_block()
                
        except Exception as e:
            print(f"⚠️ Error loading from Supabase: {e}")
            self.create_genesis_block()
    
    def create_genesis_block(self):
        """Create and save genesis block"""
        print("🚀 Creating genesis block...")
        
        genesis_block = Block(0, [], time.time(), "0")
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
        
        # Save to Supabase
        self.save_block_to_db(genesis_block)
        
        # Create system wallets
        self.create_system_wallets()
        
        print("✅ Genesis block created!")
    
    def create_system_wallets(self):
        """Create system wallets in Supabase"""
        system_wallets = [
            {"address": "system", "private_key": "system_private", "public_key": "system_public", "balance": 0},
            {"address": "ad_system", "private_key": "adsystem_private", "public_key": "adsystem_public", "balance": 0},
            {"address": "admin_wallet", "private_key": "admin_private", "public_key": "admin_public", "balance": 0}
        ]
        
        for wallet in system_wallets:
            try:
                supabase.table('wallets').insert(wallet).execute()
                print(f"✅ Created wallet: {wallet['address']}")
            except Exception as e:
                print(f"⚠️ Wallet {wallet['address']} already exists")
    
    def save_block_to_db(self, block):
        """Save block to Supabase"""
        try:
            block_dict = block.to_dict()
            # Convert timestamp to datetime string
            block_dict['timestamp'] = datetime.fromtimestamp(block_dict['timestamp']).isoformat()
            block_dict['transactions'] = json.dumps(block_dict['transactions'])
            
            supabase.table('blocks').insert(block_dict).execute()
            return True
        except Exception as e:
            print(f"❌ Error saving block: {e}")
            return False
    
    def add_transaction(self, transaction):
        """Add transaction to pending and Supabase"""
        self.pending_transactions.append(transaction)
        
        # Save to Supabase
        try:
            tx_hash = self.generate_tx_hash(transaction)
            tx_data = {
                'tx_hash': tx_hash,
                'from_address': transaction.get('from', 'system'),
                'to_address': transaction.get('to', 'system'),
                'amount': transaction.get('amount', 0),
                'token': TOKEN_SYMBOL,
                'type': transaction.get('type', 'transfer'),
                'block_index': None,
                'timestamp': datetime.fromtimestamp(transaction.get('timestamp', time.time())).isoformat(),
                'data': json.dumps(transaction)
            }
            supabase.table('transactions').insert(tx_data).execute()
        except Exception as e:
            print(f"⚠️ Error saving transaction: {e}")
    
    def generate_tx_hash(self, transaction):
        """Generate transaction hash"""
        tx_string = f"{transaction.get('from', '')}{transaction.get('to', '')}{transaction.get('amount', 0)}{transaction.get('timestamp', time.time())}"
        return hashlib.sha256(tx_string.encode()).hexdigest()[:16]
    
    def mine_pending_transactions(self, mining_reward_address):
        """Mine pending transactions"""
        if not self.pending_transactions:
            print("No pending transactions to mine")
            return None
        
        # Add mining reward
        reward_tx = {
            "from": "system",
            "to": mining_reward_address,
            "amount": self.mining_reward,
            "type": "mining_reward",
            "token": TOKEN_SYMBOL,
            "timestamp": time.time()
        }
        self.pending_transactions.append(reward_tx)
        
        # Create block
        block = Block(
            index=len(self.chain),
            transactions=self.pending_transactions,
            timestamp=time.time(),
            previous_hash=self.chain[-1].hash
        )
        
        # Mine
        block.mine_block(self.difficulty)
        self.chain.append(block)
        
        # Save to Supabase
        self.save_block_to_db(block)
        
        # Update pending transactions with block index
        for tx in self.pending_transactions:
            try:
                tx_hash = self.generate_tx_hash(tx)
                supabase.table('transactions').update({'block_index': block.index}).eq('tx_hash', tx_hash).execute()
            except Exception as e:
                print(f"⚠️ Error updating transaction: {e}")
        
        # Update wallet balances
        for tx in self.pending_transactions:
            if tx.get('to') and tx['to'] not in ['system', 'ad_system']:
                self.update_wallet_balance(tx['to'], tx.get('amount', 0))
            if tx.get('from') and tx['from'] not in ['system', 'ad_system']:
                self.update_wallet_balance(tx['from'], -tx.get('amount', 0))
        
        self.pending_transactions = []
        return block
    
    def update_wallet_balance(self, address, amount):
        """Update wallet balance in Supabase"""
        try:
            # Get current balance
            response = supabase.table('wallets').select('balance').eq('address', address).execute()
            if response.data:
                current_balance = response.data[0]['balance']
                new_balance = current_balance + amount
                supabase.table('wallets').update({'balance': new_balance}).eq('address', address).execute()
            else:
                # Create new wallet
                supabase.table('wallets').insert({
                    'address': address,
                    'private_key': f'auto_{address[:10]}',
                    'public_key': f'auto_{address[:10]}',
                    'balance': amount
                }).execute()
        except Exception as e:
            print(f"⚠️ Error updating balance for {address}: {e}")
    
    def get_balance(self, address):
        """Get wallet balance from Supabase"""
        try:
            response = supabase.table('wallets').select('balance').eq('address', address).execute()
            if response.data:
                return response.data[0]['balance']
            return 0
        except Exception:
            return 0
    
    def get_blockchain_stats(self):
        """Get blockchain statistics"""
        try:
            blocks_count = len(self.chain)
            txs_count = supabase.table('transactions').select('count', count='exact').execute()
            wallets_count = supabase.table('wallets').select('count', count='exact').execute()
            
            return {
                'total_blocks': blocks_count,
                'total_transactions': txs_count.count,
                'total_wallets': wallets_count.count,
                'total_supply': sum([w.balance for w in self.get_all_wallets()])
            }
        except Exception:
            return {
                'total_blocks': len(self.chain),
                'total_transactions': 0,
                'total_wallets': 0,
                'total_supply': 0
            }
    
    def get_all_wallets(self, limit=100):
        """Get all wallets"""
        try:
            response = supabase.table('wallets').select('*').limit(limit).order('balance', desc=True).execute()
            return response.data
        except Exception:
            return []
    
    def get_token_info(self):
        """Get token information"""
        stats = self.get_blockchain_stats()
        return {
            "name": TOKEN_NAME,
            "symbol": TOKEN_SYMBOL,
            "decimals": TOKEN_DECIMALS,
            "total_supply": TOTAL_SUPPLY,
            "circulating_supply": stats['total_supply'],
            "mining_reward": self.mining_reward,
            "ad_reward": self.ad_reward
        }
    
    def to_dict(self):
        """Convert blockchain to dictionary"""
        return {
            "chain": [block.to_dict() for block in self.chain],
            "pending_transactions": self.pending_transactions,
            "difficulty": self.difficulty,
            "mining_reward": self.mining_reward,
            "ad_reward": self.ad_reward,
            "token_info": self.get_token_info()
        }
    
    def validate_chain(self):
        """Validate the blockchain"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            if current.hash != current.calculate_hash():
                return False
            if current.previous_hash != previous.hash:
                return False
            if current.hash[:self.difficulty] != "0" * self.difficulty:
                return False
        
        return True

# Create singleton
blockchain = Blockchain()
