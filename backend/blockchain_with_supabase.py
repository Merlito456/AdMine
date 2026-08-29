import hashlib
import json
import time
import os
import random
import string
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from supabase_client import supabase_client

load_dotenv()

# ============================================
# SUPABASE CONFIGURATION
# ============================================
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://mydbvqyxoxqzluslpavh.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'sb_publishable_7An_A_PQbrrTzpyrSKOEgw_dPf5mj_o')

# ============================================
# TOKEN CONFIG - 10 TRILLION
# ============================================
TOKEN_SYMBOL = os.getenv('TOKEN_SYMBOL', 'ADT')
TOKEN_NAME = os.getenv('TOKEN_NAME', 'Ad Token')
TOKEN_DECIMALS = int(os.getenv('TOKEN_DECIMALS', 18))
TOTAL_SUPPLY = int(os.getenv('TOTAL_SUPPLY', 10_000_000_000_000))
MAX_SUPPLY = int(os.getenv('MAX_SUPPLY', 10_000_000_000_000))
GENESIS_SUPPLY = int(os.getenv('GENESIS_SUPPLY', 1_000_000_000_000))

# ============================================
# MINING CONFIG
# ============================================
MINING_REWARD = float(os.getenv('MINING_REWARD', 10))
AD_REWARD = float(os.getenv('AD_REWARD', 0.5))
DIFFICULTY = int(os.getenv('DIFFICULTY', 4))

# ============================================
# REFERRAL MODULE IMPORT
# ============================================
from referral import calculate_referral_rewards, get_referral_stats

# ============================================
# HELPER FUNCTION - GENERATE REFERRAL CODE
# ============================================
def generate_referral_code():
    """Generate a unique 8-character referral code"""
    chars = string.ascii_uppercase + string.digits
    # Avoid ambiguous characters (0, O, I, 1)
    chars = chars.replace('0', '').replace('O', '').replace('I', '').replace('1', '')
    code = ''.join(random.choices(chars, k=8))
    return code

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
        self.difficulty = DIFFICULTY
        self.mining_reward = MINING_REWARD
        self.ad_reward = AD_REWARD
        self.token_symbol = TOKEN_SYMBOL
        self.token_name = TOKEN_NAME
        self.total_supply = TOTAL_SUPPLY
        self.max_supply = MAX_SUPPLY
        self.genesis_supply = GENESIS_SUPPLY
        self.circulating_supply = 0
        
        # Time-based mining settings
        self.hourly_rate = float(os.getenv('MINING_RATE', 0.5))
        self.daily_cap = float(os.getenv('DAILY_CAP', 12.0))
        self.claim_interval_hours = int(os.getenv('CLAIM_INTERVAL', 24))
        self.mining_seconds = self.claim_interval_hours * 3600
        
        self.chain = []
        self.pending_transactions = []
        
        # Load from Supabase or create genesis
        self.load_from_db()

    def load_from_db(self):
        """Load blockchain from Supabase"""
        blocks = supabase_client.get_all_blocks(limit=1000)
        if blocks:
            blocks.sort(key=lambda x: x['index'])
            for block_data in blocks:
                block = Block(
                    index=block_data['index'],
                    transactions=json.loads(block_data['transactions']),
                    timestamp=datetime.fromisoformat(block_data['timestamp'].replace('Z', '+00:00')).timestamp(),
                    previous_hash=block_data['previous_hash'],
                    nonce=block_data['nonce']
                )
                block.hash = block_data['hash']
                self.chain.append(block)
            
            pending = supabase_client.get_pending_transactions()
            self.pending_transactions = [json.loads(tx['data']) for tx in pending]
            
            print(f"✅ Loaded {len(self.chain)} blocks from database")
        else:
            self.create_genesis_block()

    def create_genesis_block(self):
        """Create and save genesis block with 1 Trillion ADT"""
        print("🚀 Creating genesis block with 1 Trillion ADT...")
        
        self.genesis_supply = GENESIS_SUPPLY
        self.total_supply = GENESIS_SUPPLY
        self.circulating_supply = GENESIS_SUPPLY
        
        genesis_transactions = [{
            "from": "system",
            "to": "admin_wallet",
            "amount": self.genesis_supply,
            "type": "genesis",
            "token": TOKEN_SYMBOL,
            "timestamp": time.time()
        }]
        
        genesis_block = Block(0, genesis_transactions, time.time(), "0")
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
        
        supabase_client.save_block(genesis_block.to_dict())
        
        supabase_client.create_wallet("admin_wallet", "admin_private_key", "admin_public_key")
        supabase_client.update_balance("admin_wallet", self.genesis_supply)
        
        self.create_system_wallets()
        
        print(f"✅ Genesis block created!")
        print(f"🪙 Initial Supply: {self.genesis_supply:,} {TOKEN_SYMBOL}")
        print(f"📊 Max Supply: {self.max_supply:,} {TOKEN_SYMBOL}")

    def create_system_wallets(self):
        """Create system wallets"""
        system_wallets = [
            {"address": "system", "private_key": "system_private", "public_key": "system_public", "balance": 0},
            {"address": "ad_system", "private_key": "adsystem_private", "public_key": "adsystem_public", "balance": 0},
            {"address": "admin_wallet", "private_key": "admin_private", "public_key": "admin_public", "balance": self.genesis_supply}
        ]
        
        for wallet in system_wallets:
            existing = supabase_client.get_wallet(wallet['address'])
            if not existing:
                supabase_client.create_wallet(wallet['address'], wallet['private_key'], wallet['public_key'])
                if wallet['balance'] > 0:
                    supabase_client.update_balance(wallet['address'], wallet['balance'])
                print(f"✅ Created wallet: {wallet['address']}")

    def create_wallet(self, address, private_key, public_key):
        """Create a new wallet with auto-generated referral code"""
        # Create wallet
        result = supabase_client.create_wallet(address, private_key, public_key)
        
        # Auto-generate referral code
        if result:
            # Generate unique 8-character code
            code = generate_referral_code()
            
            # Ensure uniqueness
            attempts = 0
            while attempts < 10:
                existing = supabase_client.get_wallet_by_referral_code(code)
                if not existing:
                    break
                code = generate_referral_code()
                attempts += 1
            
            # Save referral code to wallet
            supabase_client.update_wallet(address, {'referral_code': code})
            print(f"✅ Auto-generated referral code for {address}: {code}")
            
            # Return the created wallet with referral code
            wallet = supabase_client.get_wallet(address)
            if wallet:
                wallet['referral_code'] = code
            
            return wallet
        
        return result

    def get_latest_block(self):
        return self.chain[-1]

    def add_transaction(self, transaction):
        self.pending_transactions.append(transaction)
        tx_data = transaction.copy()
        tx_data['block_index'] = None
        supabase_client.save_transaction(tx_data)

    def update_wallet_balance(self, address, amount):
        """Update wallet balance"""
        supabase_client.update_balance(address, amount)

    def mine_pending_transactions(self, mining_reward_address):
        if not self.pending_transactions:
            return None
        
        if self.total_supply + self.mining_reward > self.max_supply:
            print(f"⚠️ Cannot mine: Would exceed max supply of {self.max_supply:,}")
            return None
        
        reward_tx = {
            "from": "system",
            "to": mining_reward_address,
            "amount": self.mining_reward,
            "type": "mining_reward",
            "token": TOKEN_SYMBOL,
            "timestamp": time.time()
        }
        self.pending_transactions.append(reward_tx)
        
        self.total_supply += self.mining_reward
        self.circulating_supply += self.mining_reward

        block = Block(
            index=len(self.chain),
            transactions=self.pending_transactions,
            timestamp=time.time(),
            previous_hash=self.get_latest_block().hash
        )

        block.mine_block(self.difficulty)
        self.chain.append(block)
        
        block_dict = block.to_dict()
        supabase_client.save_block(block_dict)
        
        for tx in self.pending_transactions:
            tx['block_index'] = block.index
            supabase_client.save_transaction(tx)
        
        for tx in self.pending_transactions:
            if tx.get('to'):
                wallet = supabase_client.get_wallet(tx['to'])
                if wallet:
                    supabase_client.update_balance(tx['to'], wallet['balance'] + tx['amount'])
            if tx.get('from') not in ['system', 'ad_system']:
                wallet = supabase_client.get_wallet(tx['from'])
                if wallet:
                    supabase_client.update_balance(tx['from'], wallet['balance'] - tx['amount'])
        
        self.pending_transactions = []
        return block

    def get_balance(self, address):
        return supabase_client.get_wallet(address)['balance'] if supabase_client.get_wallet(address) else 0

    def get_all_wallets(self, limit=100):
        return supabase_client.get_all_wallets(limit)

    def get_blockchain_stats(self):
        stats = supabase_client.get_blockchain_stats()
        stats['total_supply'] = self.total_supply
        stats['max_supply'] = self.max_supply
        stats['genesis_supply'] = self.genesis_supply
        stats['circulating_supply'] = self.circulating_supply
        stats['hourly_mining_rate'] = self.hourly_rate
        stats['daily_mining_cap'] = self.daily_cap
        return stats

    def get_token_info(self):
        stats = self.get_blockchain_stats()
        return {
            "name": TOKEN_NAME,
            "symbol": TOKEN_SYMBOL,
            "decimals": TOKEN_DECIMALS,
            "total_supply": self.total_supply,
            "max_supply": self.max_supply,
            "genesis_supply": self.genesis_supply,
            "circulating_supply": stats['circulating_supply'],
            "mining_reward": self.mining_reward,
            "ad_reward": self.ad_reward,
            "difficulty": self.difficulty
        }

    def to_dict(self):
        return {
            "chain": [block.to_dict() for block in self.chain],
            "pending_transactions": self.pending_transactions,
            "difficulty": self.difficulty,
            "mining_reward": self.mining_reward,
            "ad_reward": self.ad_reward,
            "token_info": self.get_token_info()
        }

    def validate_chain(self):
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
    # TIME-BASED MINING METHODS WITH SESSION TRACKING & REFERRAL REWARDS
    # ============================================

    def start_mining(self, address):
        """Start mining for a wallet and record session"""
        wallet = supabase_client.get_wallet(address)
        if not wallet:
            return {"error": "Wallet not found"}
        
        if wallet.get('mining_active', False):
            return {"error": "Already mining"}
        
        now = datetime.now(timezone.utc)
        
        # Update wallet mining status
        supabase_client.update_mining_status(address, True, now.isoformat())
        
        # Create mining session in database
        try:
            session_data = {
                'wallet_address': address,
                'start_time': now.isoformat(),
                'status': 'active',
                'hourly_rate': self.hourly_rate,
                'reward_amount': 0,
                'reward_earned': 0,
                'duration_seconds': 0
            }
            result = supabase_client.create_mining_session(session_data)
            if result:
                print(f"✅ Mining session created for {address}, ID: {result.get('id')}")
            else:
                print(f"⚠️ Failed to create mining session for {address}")
        except Exception as e:
            print(f"⚠️ Error creating mining session: {e}")
        
        return {
            "status": "success",
            "message": "Mining started!",
            "address": address,
            "rate": self.hourly_rate,
            "hourly_rate": f"{self.hourly_rate} {TOKEN_SYMBOL}/hour",
            "daily_cap": f"{self.daily_cap} {TOKEN_SYMBOL}/day",
            "session_started": now.isoformat()
        }

    def stop_mining(self, address):
        """Stop mining and claim rewards with referral bonuses"""
        wallet = supabase_client.get_wallet(address)
        if not wallet:
            return {"error": "Wallet not found"}
        
        if not wallet.get('mining_active', False):
            return {"error": "Not mining"}
        
        mining_started = datetime.fromisoformat(wallet['mining_started'])
        if mining_started.tzinfo is None:
            mining_started = mining_started.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        mining_duration = (now - mining_started).total_seconds()
        reward = (mining_duration / 3600) * self.hourly_rate
        reward = min(reward, self.daily_cap)
        
        current_balance = wallet.get('balance', 0)
        total_mined = wallet.get('total_mined', 0) + reward
        
        # ============================================
        # REFERRAL REWARDS CALCULATION
        # ============================================
        referral_rewards_distributed = []
        if reward > 0:
            try:
                referral_rewards = calculate_referral_rewards(address, reward)
                if referral_rewards:
                    for reward_info in referral_rewards:
                        print(f"✅ Referral reward: {reward_info['amount']} {TOKEN_SYMBOL} to {reward_info['address']} (Level {reward_info['level']})")
                        referral_rewards_distributed.append(reward_info)
                else:
                    print(f"ℹ️ No referral rewards for {address}")
            except Exception as e:
                print(f"⚠️ Error calculating referral rewards: {e}")
        
        # Update wallet
        supabase_client.update_mining_status(address, False, None, current_balance + reward, total_mined)
        
        # Update mining session
        try:
            active_session = supabase_client.get_active_mining_session(address)
            if active_session:
                updated = supabase_client.update_mining_session(
                    active_session['id'],
                    now.isoformat(),
                    'completed',
                    reward,
                    int(mining_duration)
                )
                if updated:
                    print(f"✅ Mining session updated for {address}, reward: {reward}")
                else:
                    print(f"⚠️ Failed to update mining session for {address}")
            else:
                session_data = {
                    'wallet_address': address,
                    'start_time': mining_started.isoformat(),
                    'end_time': now.isoformat(),
                    'status': 'completed',
                    'hourly_rate': self.hourly_rate,
                    'reward_earned': reward,
                    'reward_amount': reward,
                    'duration_seconds': int(mining_duration)
                }
                result = supabase_client.create_mining_session(session_data)
                if result:
                    print(f"✅ Mining session created for {address} (fallback)")
                else:
                    print(f"⚠️ Failed to create mining session for {address} (fallback)")
        except Exception as e:
            print(f"⚠️ Error updating mining session: {e}")
        
        self.total_supply += reward
        self.circulating_supply += reward
        
        transaction = {
            "from": "mining_system",
            "to": address,
            "amount": reward,
            "type": "mining_reward",
            "token": TOKEN_SYMBOL,
            "timestamp": time.time()
        }
        self.add_transaction(transaction)
        
        return {
            "status": "success",
            "message": f"Mining stopped! Earned {reward:.4f} {TOKEN_SYMBOL}",
            "address": address,
            "reward": reward,
            "duration": f"{mining_duration/3600:.2f} hours",
            "new_balance": current_balance + reward,
            "session_completed": now.isoformat(),
            "referral_rewards": referral_rewards_distributed
        }

    def get_mining_status(self, address):
        """Get mining status from wallet"""
        wallet = supabase_client.get_wallet(address)
        if not wallet:
            return {"error": "Wallet not found"}
        
        # Also check for active session
        active_session = supabase_client.get_active_mining_session(address)
        
        if not wallet.get('mining_active', False):
            return {
                "status": "inactive",
                "address": address,
                "rate": self.hourly_rate,
                "daily_cap": self.daily_cap,
                "has_session": active_session is not None
            }
        
        mining_started = datetime.fromisoformat(wallet['mining_started'])
        if mining_started.tzinfo is None:
            mining_started = mining_started.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        mining_duration = (now - mining_started).total_seconds()
        reward = (mining_duration / 3600) * self.hourly_rate
        reward = min(reward, self.daily_cap)
        
        return {
            "status": "active",
            "address": address,
            "duration": f"{mining_duration/3600:.2f} hours",
            "reward_so_far": f"{reward:.4f} {TOKEN_SYMBOL}",
            "hourly_rate": f"{self.hourly_rate} {TOKEN_SYMBOL}/hour",
            "daily_cap": f"{self.daily_cap} {TOKEN_SYMBOL}/day",
            "session_id": active_session['id'] if active_session else None,
            "session_started": wallet.get('mining_started')
        }

    def get_mining_stats(self, address):
        """Get mining statistics"""
        wallet = supabase_client.get_wallet(address)
        if not wallet:
            return {"error": "Wallet not found"}
        
        sessions = supabase_client.get_mining_sessions(address)
        total_earned = sum([s.get('reward_earned', 0) for s in sessions]) if sessions else 0
        
        # Get referral stats
        referral_stats = get_referral_stats(address)
        
        return {
            "address": address,
            "total_mined": wallet.get('total_mined', 0),
            "balance": wallet.get('balance', 0),
            "mining_active": wallet.get('mining_active', False),
            "total_sessions": len(sessions),
            "total_earned": total_earned,
            "hourly_rate": self.hourly_rate,
            "daily_cap": self.daily_cap,
            "referral_stats": referral_stats
        }

    def get_mining_sessions(self, address, limit=50):
        """Get all mining sessions for a wallet"""
        return supabase_client.get_mining_sessions(address, limit)

    def update_mining_config(self, hourly_rate=None, daily_cap=None, claim_interval=None):
        """Update mining configuration"""
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

# ============================================
# CREATE SINGLETON INSTANCE
# ============================================
try:
    blockchain = Blockchain()
    print(f"✅ Blockchain initialized with {len(blockchain.chain)} blocks")
    print(f"🪙 Total Supply: {blockchain.total_supply:,} {TOKEN_SYMBOL}")
    print(f"📊 Max Supply: {blockchain.max_supply:,} {TOKEN_SYMBOL}")
    print(f"⛏️ Mining Rate: {blockchain.hourly_rate} {TOKEN_SYMBOL}/hour")
    print(f"📈 Daily Cap: {blockchain.daily_cap} {TOKEN_SYMBOL}/day")
    print(f"🔗 Referral System: 5% Level 1, 2% Level 2")
    print(f"🔑 Auto-generated referral codes on wallet creation")
except Exception as e:
    print(f"❌ Error initializing blockchain: {e}")
    blockchain = None

# Export
__all__ = ['blockchain', 'TOKEN_SYMBOL', 'TOKEN_NAME']
