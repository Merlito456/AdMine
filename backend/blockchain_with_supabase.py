import hashlib
import json
import time
import os
from datetime import datetime, timedelta, timezone
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
# MINING CONFIG (Time-Based)
# ============================================
MINING_CONFIG = {
    'hourly_rate': 0.5,  # ADT per hour
    'daily_cap': 12.0,   # Max ADT per 24 hours
    'claim_interval_hours': 24,  # Claim every 24 hours
    'mining_seconds': 86400,  # 24 hours in seconds
}

# ============================================
# BLOCK CLASS (Simplified - Only for ledger)
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
# BLOCKCHAIN CLASS (Time-Based Mining)
# ============================================
class Blockchain:
    def __init__(self):
        self.difficulty = int(os.getenv('DIFFICULTY', 4))
        
        # Time-based mining settings
        self.hourly_rate = float(os.getenv('MINING_RATE', MINING_CONFIG['hourly_rate']))
        self.daily_cap = float(os.getenv('DAILY_CAP', MINING_CONFIG['daily_cap']))
        self.claim_interval_hours = int(os.getenv('CLAIM_INTERVAL', MINING_CONFIG['claim_interval_hours']))
        self.mining_seconds = self.claim_interval_hours * 3600
        
        # Supply tracking
        self.total_supply = 0
        self.circulating_supply = 0
        self.burned_supply = 0
        self.minted_supply = 0
        self.genesis_supply = 0
        self.max_supply = MAX_SUPPLY
        
        self.chain = []
        self.pending_transactions = []
        
        # Load from Supabase
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
                
                # Load mining sessions
                self.load_mining_sessions()
                
                print(f"✅ Loaded {len(self.chain)} blocks from Supabase")
            else:
                self.create_genesis_block()
                
        except Exception as e:
            print(f"⚠️ Error loading from Supabase: {e}")
            self.create_genesis_block()
    
    def load_mining_sessions(self):
        """Load mining sessions from Supabase"""
        if not supabase:
            return
        
        try:
            # Create mining_sessions table if needed
            self.create_mining_tables()
        except Exception as e:
            print(f"⚠️ Error loading mining sessions: {e}")
    
    def create_mining_tables(self):
        """Create mining tables if they don't exist"""
        if not supabase:
            return
        
        try:
            # Check if mining_sessions table exists
            supabase.table('mining_sessions').select('*').limit(1).execute()
        except:
            # Table will be created via SQL
            print("📊 Mining tables need to be created via SQL")
    
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
            self.update_wallet_balance("admin_wallet", self.genesis_supply)
        
        # Create system wallets
        self.create_system_wallets()
        
        print(f"✅ Genesis block created! Total Supply: {self.total_supply} {TOKEN_SYMBOL}")
    
    def create_system_wallets(self):
        """Create system wallets in Supabase"""
        if not supabase:
            return
            
        system_wallets = [
            {"address": "system", "private_key": "system_private", "public_key": "system_public", "balance": 0},
            {"address": "ad_system", "private_key": "adsystem_private", "public_key": "adsystem_public", "balance": 0},
            {"address": "admin_wallet", "private_key": "admin_private", "public_key": "admin_public", "balance": 10000}
        ]
        
        for wallet in system_wallets:
            try:
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
                "balance": 0,
                "last_mining_claim": None,
                "total_mined": 0,
                "mining_active": False
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
    
    # ============================================
    # TIME-BASED MINING METHODS
    # ============================================
    
    def start_mining(self, address):
        """Start a mining session for a wallet"""
        if not supabase:
            return {"error": "Database not connected"}
        
        try:
            # Check if wallet exists
            response = supabase.table('wallets').select('*').eq('address', address).execute()
            if not response.data:
                return {"error": "Wallet not found"}
            
            wallet = response.data[0]
            
            # Check if already mining
            if wallet.get('mining_active', False):
                return {"error": "Already mining"}
            
            # Use UTC timezone
            now = datetime.now(timezone.utc)
            
            # Start mining session
            supabase.table('wallets').update({
                'mining_active': True,
                'mining_started': now.isoformat(),
                'mining_last_claim': now.isoformat(),
                'mining_accumulated': 0
            }).eq('address', address).execute()
            
            return {
                "status": "success",
                "message": "Mining started!",
                "address": address,
                "rate": self.hourly_rate,
                "hourly_rate": f"{self.hourly_rate} {TOKEN_SYMBOL}/hour",
                "daily_cap": f"{self.daily_cap} {TOKEN_SYMBOL}/day"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def stop_mining(self, address):
        """Stop mining and calculate rewards"""
        if not supabase:
            return {"error": "Database not connected"}
        
        try:
            # Get wallet
            response = supabase.table('wallets').select('*').eq('address', address).execute()
            if not response.data:
                return {"error": "Wallet not found"}
            
            wallet = response.data[0]
            
            if not wallet.get('mining_active', False):
                return {"error": "Not mining"}
            
            # Parse time with UTC
            mining_started = datetime.fromisoformat(wallet['mining_started'])
            if mining_started.tzinfo is None:
                mining_started = mining_started.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            mining_duration = (now - mining_started).total_seconds()
            
            # Calculate reward (capped at daily limit)
            reward = (mining_duration / 3600) * self.hourly_rate
            reward = min(reward, self.daily_cap)
            
            # Update wallet
            current_balance = wallet.get('balance', 0)
            total_mined = wallet.get('total_mined', 0) + reward
            
            supabase.table('wallets').update({
                'mining_active': False,
                'balance': current_balance + reward,
                'total_mined': total_mined,
                'mining_accumulated': wallet.get('mining_accumulated', 0) + reward
            }).eq('address', address).execute()
            
            # Update supply
            self.total_supply += reward
            self.circulating_supply += reward
            
            # Record transaction
            transaction = {
                "from": "mining_system",
                "to": address,
                "amount": reward,
                "type": "mining_reward",
                "token": TOKEN_SYMBOL,
                "timestamp": time.time(),
                "duration": mining_duration,
                "rate": self.hourly_rate
            }
            self.add_transaction(transaction)
            
            return {
                "status": "success",
                "message": f"Mining stopped! Earned {reward:.4f} {TOKEN_SYMBOL}",
                "address": address,
                "reward": reward,
                "duration": f"{mining_duration/3600:.2f} hours",
                "total_mined": total_mined,
                "new_balance": current_balance + reward
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_mining_status(self, address):
        """Get current mining status for a wallet"""
        if not supabase:
            return {"error": "Database not connected"}
        
        try:
            response = supabase.table('wallets').select('*').eq('address', address).execute()
            if not response.data:
                return {"error": "Wallet not found"}
            
            wallet = response.data[0]
            
            if not wallet.get('mining_active', False):
                return {
                    "status": "inactive",
                    "address": address,
                    "message": "Not currently mining",
                    "rate": self.hourly_rate,
                    "daily_cap": self.daily_cap
                }
            
            # Parse with UTC
            mining_started = datetime.fromisoformat(wallet['mining_started'])
            if mining_started.tzinfo is None:
                mining_started = mining_started.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            mining_duration = (now - mining_started).total_seconds()
            
            # Calculate reward so far
            reward = (mining_duration / 3600) * self.hourly_rate
            reward = min(reward, self.daily_cap)
            
            return {
                "status": "active",
                "address": address,
                "mining_started": wallet['mining_started'],
                "duration": f"{mining_duration/3600:.2f} hours",
                "reward_so_far": f"{reward:.4f} {TOKEN_SYMBOL}",
                "hourly_rate": f"{self.hourly_rate} {TOKEN_SYMBOL}/hour",
                "daily_cap": f"{self.daily_cap} {TOKEN_SYMBOL}/day",
                "balance": wallet.get('balance', 0)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def claim_daily_reward(self, address):
        """Claim accumulated mining rewards"""
        if not supabase:
            return {"error": "Database not connected"}
        
        try:
            response = supabase.table('wallets').select('*').eq('address', address).execute()
            if not response.data:
                return {"error": "Wallet not found"}
            
            wallet = response.data[0]
            
            if not wallet.get('mining_active', False):
                return {"error": "Not mining"}
            
            # Parse with UTC
            last_claim = datetime.fromisoformat(wallet.get('mining_last_claim', wallet['mining_started']))
            if last_claim.tzinfo is None:
                last_claim = last_claim.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            
            if (now - last_claim).total_seconds() < self.mining_seconds:
                remaining = self.mining_seconds - (now - last_claim).total_seconds()
                return {
                    "error": f"Can only claim every {self.claim_interval_hours} hours",
                    "remaining": f"{remaining/3600:.2f} hours",
                    "next_claim": (last_claim + timedelta(hours=self.claim_interval_hours)).isoformat()
                }
            
            # Calculate reward
            mining_started = datetime.fromisoformat(wallet['mining_started'])
            if mining_started.tzinfo is None:
                mining_started = mining_started.replace(tzinfo=timezone.utc)
            
            mining_duration = (now - mining_started).total_seconds()
            reward = (mining_duration / 3600) * self.hourly_rate
            reward = min(reward, self.daily_cap)
            
            # Update wallet
            current_balance = wallet.get('balance', 0)
            total_mined = wallet.get('total_mined', 0) + reward
            accumulated = wallet.get('mining_accumulated', 0) + reward
            
            supabase.table('wallets').update({
                'balance': current_balance + reward,
                'total_mined': total_mined,
                'mining_accumulated': accumulated,
                'mining_last_claim': now.isoformat()
            }).eq('address', address).execute()
            
            # Update supply
            self.total_supply += reward
            self.circulating_supply += reward
            
            return {
                "status": "success",
                "message": f"Claimed {reward:.4f} {TOKEN_SYMBOL}",
                "address": address,
                "reward": reward,
                "new_balance": current_balance + reward,
                "total_mined": total_mined
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_mining_stats(self, address):
        """Get mining statistics for a wallet"""
        if not supabase:
            return {"error": "Database not connected"}
        
        try:
            response = supabase.table('wallets').select('*').eq('address', address).execute()
            if not response.data:
                return {"error": "Wallet not found"}
            
            wallet = response.data[0]
            
            return {
                "address": address,
                "total_mined": wallet.get('total_mined', 0),
                "mining_accumulated": wallet.get('mining_accumulated', 0),
                "mining_active": wallet.get('mining_active', False),
                "mining_started": wallet.get('mining_started'),
                "last_claim": wallet.get('mining_last_claim'),
                "balance": wallet.get('balance', 0),
                "hourly_rate": self.hourly_rate,
                "daily_cap": self.daily_cap
            }
        except Exception as e:
            return {"error": str(e)}
    
    def update_mining_config(self, hourly_rate=None, daily_cap=None, claim_interval=None):
        """Update mining configuration (Admin only)"""
        if hourly_rate is not None:
            self.hourly_rate = float(hourly_rate)
        if daily_cap is not None:
            self.daily_cap = float(daily_cap)
        if claim_interval is not None:
            self.claim_interval_hours = int(claim_interval)
            self.mining_seconds = self.claim_interval_hours * 3600
        
        return {
            "status": "success",
            "hourly_rate": self.hourly_rate,
            "daily_cap": self.daily_cap,
            "claim_interval_hours": self.claim_interval_hours
        }
    
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
            'max_supply': self.max_supply,
            'hourly_mining_rate': self.hourly_rate,
            'daily_mining_cap': self.daily_cap
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
            "mining_hourly_rate": self.hourly_rate,
            "mining_daily_cap": self.daily_cap,
            "claim_interval_hours": self.claim_interval_hours
        }
    
    def to_dict(self):
        """Convert blockchain to dictionary"""
        return {
            "chain": [block.to_dict() for block in self.chain],
            "pending_transactions": self.pending_transactions,
            "difficulty": self.difficulty,
            "mining_hourly_rate": self.hourly_rate,
            "mining_daily_cap": self.daily_cap,
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
        
        return True

# ============================================
# CREATE SINGLETON INSTANCE
# ============================================
try:
    blockchain = Blockchain()
    print(f"✅ Blockchain initialized with {len(blockchain.chain)} blocks")
    print(f"⛏️ Mining Rate: {blockchain.hourly_rate} {TOKEN_SYMBOL}/hour")
    print(f"📊 Daily Cap: {blockchain.daily_cap} {TOKEN_SYMBOL}/day")
except Exception as e:
    print(f"❌ Error initializing blockchain: {e}")
    blockchain = None

# ============================================
# EXPORT FOR IMPORT
# ============================================
__all__ = ['blockchain', 'TOKEN_SYMBOL', 'TOKEN_NAME', 'supabase']
