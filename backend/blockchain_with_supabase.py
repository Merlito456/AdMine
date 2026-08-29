import hashlib
import json
import time
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ============================================
# SUPABASE CONFIGURATION
# ============================================
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://mydbvqyxoxqzluslpavh.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'sb_publishable_7An_A_PQbrrTzpyrSKOEgw_dPf5mj_o')

# Initialize Supabase
try:
    from supabase import create_client, Client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"✅ Supabase connected to {SUPABASE_URL}")
except Exception as e:
    print(f"❌ Supabase connection error: {e}")
    supabase = None

# ============================================
# TOKEN CONFIG
# ============================================
TOKEN_SYMBOL = "ADT"
TOKEN_NAME = "Ad Token"
TOKEN_DECIMALS = 18
MAX_SUPPLY = 100_000_000

# ============================================
# BLOCK CLASS
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

# ============================================
# BLOCKCHAIN CLASS
# ============================================
class Blockchain:
    def __init__(self):
        self.difficulty = int(os.getenv('DIFFICULTY', 4))
        self.mining_reward = float(os.getenv('MINING_REWARD', 10))
        self.ad_reward = float(os.getenv('AD_REWARD', 0.5))
        
        # Supply tracking at blockchain level
        self.total_supply = 0
        self.circulating_supply = 0
        self.burned_supply = 0
        self.minted_supply = 0
        self.genesis_supply = 0
        self.max_supply = MAX_SUPPLY
        
        self.chain = []
        self.pending_transactions = []
        
        # Load from Supabase or create genesis
        self.load_from_db()
    
    def load_from_db(self):
        """Load blockchain from Supabase"""
        if not supabase:
            print("⚠️ Supabase not connected, creating fresh blockchain")
            self.create_genesis_block()
            return
        
        try:
            # Get all blocks
            response = supabase.table('blocks').select('*').order('index', desc=False).execute()
            blocks = response.data if hasattr(response, 'data') else []
            
            if blocks:
                for block_data in blocks:
                    block = Block(
                        index=block_data['index'],
                        transactions=json.loads(block_data['transactions']) if isinstance(block_data['transactions'], str) else block_data['transactions'],
                        timestamp=block_data['timestamp'],
                        previous_hash=block_data['previous_hash'],
                        nonce=block_data['nonce']
                    )
                    block.hash = block_data['hash']
                    self.chain.append(block)
                
                # Load pending transactions
                pending_resp = supabase.table('transactions').select('*').is_('block_index', 'null').execute()
                pending = pending_resp.data if hasattr(pending_resp, 'data') else []
                self.pending_transactions = [json.loads(tx['data']) if isinstance(tx['data'], str) else tx['data'] for tx in pending]
                
                # Load supply config
                self.load_supply_config()
                
                print(f"✅ Loaded {len(self.chain)} blocks from Supabase")
            else:
                self.create_genesis_block()
                
        except Exception as e:
            print(f"⚠️ Error loading from Supabase: {e}")
            self.create_genesis_block()
    
    def load_supply_config(self):
        """Load supply data from Supabase config"""
        if not supabase:
            return
            
        try:
            # Check if config table exists, if not create it
            try:
                supabase.table('config').select('*').limit(1).execute()
            except:
                # Create config table if it doesn't exist
                supabase.table('config').insert({'key': 'init', 'value': 'init'}).execute()
                supabase.table('config').delete().eq('key', 'init').execute()
            
            response = supabase.table('config').select('*').eq('key', 'supply_data').execute()
            if response.data:
                supply_data = json.loads(response.data[0]['value'])
                self.total_supply = supply_data.get('total_supply', 0)
                self.circulating_supply = supply_data.get('circulating_supply', 0)
                self.burned_supply = supply_data.get('burned_supply', 0)
                self.minted_supply = supply_data.get('minted_supply', 0)
                self.genesis_supply = supply_data.get('genesis_supply', 0)
                self.max_supply = supply_data.get('max_supply', MAX_SUPPLY)
        except Exception as e:
            print(f"⚠️ Error loading supply config: {e}")
    
    def save_supply_config(self):
        """Save supply data to Supabase config"""
        if not supabase:
            return
            
        try:
            config_data = {
                "key": "supply_data",
                "value": json.dumps({
                    "total_supply": self.total_supply,
                    "circulating_supply": self.circulating_supply,
                    "burned_supply": self.burned_supply,
                    "minted_supply": self.minted_supply,
                    "genesis_supply": self.genesis_supply,
                    "max_supply": self.max_supply,
                    "updated_at": datetime.utcnow().isoformat()
                })
            }
            # Check if exists
            response = supabase.table('config').select('*').eq('key', 'supply_data').execute()
            if response.data:
                supabase.table('config').update(config_data).eq('key', 'supply_data').execute()
            else:
                supabase.table('config').insert(config_data).execute()
        except Exception as e:
            print(f"⚠️ Error saving supply config: {e}")
    
    def create_genesis_block(self):
        """Create and save genesis block"""
        print("🚀 Creating genesis block...")
        
        # Set initial supply
        self.genesis_supply = 10000
        self.total_supply = self.genesis_supply
        self.circulating_supply = self.genesis_supply
        
        # Create genesis transactions
        genesis_transactions = [
            {
                "from": "system",
                "to": "admin_wallet",
                "amount": self.genesis_supply,
                "type": "genesis",
                "token": TOKEN_SYMBOL,
                "timestamp": time.time()
            }
        ]
        
        genesis_block = Block(0, genesis_transactions, time.time(), "0")
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
        
        # Save to Supabase
        if supabase:
            self.save_block_to_db(genesis_block)
            # Create admin wallet with genesis supply
            self.update_wallet_balance("admin_wallet", self.genesis_supply)
        
        # Create system wallets
        self.create_system_wallets()
        
        # Save supply config
        self.save_supply_config()
        
        print(f"✅ Genesis block created! Total Supply: {self.total_supply} {TOKEN_SYMBOL}")
    
    def create_system_wallets(self):
        """Create system wallets in Supabase"""
        if not supabase:
            return
            
        system_wallets = [
            {"address": "system", "private_key": "system_private", "public_key": "system_public", "balance": 0},
            {"address": "ad_system", "private_key": "adsystem_private", "public_key": "adsystem_public", "balance": 0},
            {"address": "admin_wallet", "private_key": "admin_private", "public_key": "admin_public", "balance": 0}
        ]
        
        for wallet in system_wallets:
            try:
                # Check if exists first
                response = supabase.table('wallets').select('*').eq('address', wallet['address']).execute()
                if not response.data:
                    supabase.table('wallets').insert(wallet).execute()
                    print(f"✅ Created wallet: {wallet['address']}")
            except Exception as e:
                pass
    
    def create_wallet(self, address, private_key, public_key):
        """Create a new wallet"""
        if not supabase:
            return
        
        try:
            response = supabase.table('wallets').select('*').eq('address', address).execute()
            if response.data:
                return
            
            wallet_data = {
                "address": address,
                "private_key": private_key,
                "public_key": public_key,
                "balance": 0
            }
            supabase.table('wallets').insert(wallet_data).execute()
            print(f"✅ Created wallet: {address}")
        except Exception as e:
            print(f"⚠️ Error creating wallet: {e}")
    
    def save_block_to_db(self, block):
        """Save block to Supabase"""
        if not supabase:
            return False
            
        try:
            block_dict = block.to_dict()
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
        
        if not supabase:
            return
            
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
    
    def update_wallet_balance(self, address, amount):
        """Update wallet balance in Supabase"""
        if not supabase:
            return
            
        try:
            response = supabase.table('wallets').select('balance').eq('address', address).execute()
            if response.data:
                current_balance = response.data[0]['balance']
                new_balance = current_balance + amount
                supabase.table('wallets').update({'balance': new_balance}).eq('address', address).execute()
            else:
                supabase.table('wallets').insert({
                    'address': address,
                    'private_key': f'auto_{address[:10]}',
                    'public_key': f'auto_{address[:10]}',
                    'balance': amount if amount > 0 else 0
                }).execute()
        except Exception as e:
            print(f"⚠️ Error updating balance for {address}: {e}")
    
    def mine_pending_transactions(self, mining_reward_address):
        """Mine pending transactions"""
        if not self.pending_transactions:
            return None
        
        # Check max supply
        if self.total_supply + self.mining_reward > self.max_supply:
            print(f"⚠️ Cannot mine: Would exceed max supply of {self.max_supply}")
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
        
        # Update supply
        self.total_supply += self.mining_reward
        self.circulating_supply += self.mining_reward
        
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
        if supabase:
            self.save_block_to_db(block)
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
        self.save_supply_config()
        
        return block
    
    def get_balance(self, address):
        """Get wallet balance from Supabase"""
        if not supabase:
            return 0
            
        try:
            response = supabase.table('wallets').select('balance').eq('address', address).execute()
            if response.data:
                return response.data[0]['balance']
            return 0
        except Exception:
            return 0
    
    def get_all_wallets(self, limit=100):
        """Get all wallets"""
        if not supabase:
            return []
            
        try:
            response = supabase.table('wallets').select('*').limit(limit).order('balance', desc=True).execute()
            return response.data if hasattr(response, 'data') else []
        except Exception:
            return []
    
    def get_blockchain_stats(self):
        """Get blockchain statistics"""
        stats = {
            'total_blocks': len(self.chain),
            'total_transactions': 0,
            'total_wallets': 0,
            'total_supply': self.total_supply,
            'circulating_supply': self.circulating_supply,
            'burned_supply': self.burned_supply,
            'minted_supply': self.minted_supply,
            'genesis_supply': self.genesis_supply,
            'max_supply': self.max_supply
        }
        
        if not supabase:
            return stats
            
        try:
            tx_resp = supabase.table('transactions').select('*', count='exact').execute()
            stats['total_transactions'] = len(tx_resp.data) if hasattr(tx_resp, 'data') else 0
            
            wallet_resp = supabase.table('wallets').select('*', count='exact').execute()
            stats['total_wallets'] = len(wallet_resp.data) if hasattr(wallet_resp, 'data') else 0
            
        except Exception as e:
            print(f"⚠️ Error getting stats: {e}")
            
        return stats
    
    def get_token_info(self):
        """Get token information"""
        stats = self.get_blockchain_stats()
        return {
            "name": TOKEN_NAME,
            "symbol": TOKEN_SYMBOL,
            "decimals": TOKEN_DECIMALS,
            "total_supply": stats['total_supply'],
            "circulating_supply": stats['circulating_supply'],
            "burned_supply": stats['burned_supply'],
            "minted_supply": stats['minted_supply'],
            "genesis_supply": stats['genesis_supply'],
            "max_supply": stats['max_supply'],
            "mining_reward": self.mining_reward,
            "ad_reward": self.ad_reward,
            "difficulty": self.difficulty
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

# ============================================
# CREATE SINGLETON INSTANCE
# ============================================
try:
    blockchain = Blockchain()
    print(f"✅ Blockchain initialized with {len(blockchain.chain)} blocks")
except Exception as e:
    print(f"❌ Error initializing blockchain: {e}")
    blockchain = None

# ============================================
# EXPORT
# ============================================
__all__ = ['blockchain', 'TOKEN_SYMBOL', 'TOKEN_NAME', 'supabase']
