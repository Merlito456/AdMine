import hashlib
import json
import time
import os
from typing import List, Dict, Any
from datetime import datetime
from supabase_client import supabase_client
from dotenv import load_dotenv

load_dotenv()

# ============================================
# TOKEN CONFIGURATION - From Environment
# ============================================
TOKEN_SYMBOL = os.getenv('TOKEN_SYMBOL', 'ADT')
TOKEN_NAME = os.getenv('TOKEN_NAME', 'Ad Token')
TOKEN_DECIMALS = int(os.getenv('TOKEN_DECIMALS', 18))
TOTAL_SUPPLY = int(os.getenv('TOTAL_SUPPLY', 10_000_000_000_000))  # 10 Trillion ADT
MAX_SUPPLY = int(os.getenv('MAX_SUPPLY', 10_000_000_000_000))     # 10 Trillion Max Supply
GENESIS_SUPPLY = int(os.getenv('GENESIS_SUPPLY', 1_000_000_000_000))  # 1 Trillion

# ============================================
# MINING CONFIGURATION
# ============================================
MINING_REWARD = float(os.getenv('MINING_REWARD', 10))
AD_REWARD = float(os.getenv('AD_REWARD', 0.5))
DIFFICULTY = int(os.getenv('DIFFICULTY', 4))

# Print config on startup
print(f"🪙 Token: {TOKEN_SYMBOL} - {TOKEN_NAME}")
print(f"📊 Total Supply: {TOTAL_SUPPLY:,}")
print(f"📈 Max Supply: {MAX_SUPPLY:,}")
print(f"🎯 Genesis Supply: {GENESIS_SUPPLY:,}")

class Block:
    def __init__(self, index: int, transactions: List[Dict], timestamp: float, 
                 previous_hash: str, nonce: int = 0):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_string = json.dumps({
            "index": self.index,
            "transactions": self.transactions,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty: int) -> None:
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
        print(f"Block mined: {self.hash}")

    def to_dict(self) -> Dict:
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
        self.difficulty = DIFFICULTY
        self.mining_reward = MINING_REWARD
        self.ad_reward = AD_REWARD
        self.token_symbol = TOKEN_SYMBOL
        self.token_name = TOKEN_NAME
        self.total_supply = TOTAL_SUPPLY
        self.max_supply = MAX_SUPPLY
        self.genesis_supply = GENESIS_SUPPLY
        self.circulating_supply = 0
        
        # Load chain from database or create genesis
        self.chain = []
        self.pending_transactions = []
        self.load_chain()
        
        if not self.chain:
            self.create_genesis_block()

    def load_chain(self):
        """Load blockchain from Supabase"""
        blocks = supabase_client.get_all_blocks(limit=1000)
        if blocks:
            # Sort by index
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
            
            # Load pending transactions
            pending = supabase_client.get_pending_transactions()
            self.pending_transactions = [json.loads(tx['data']) for tx in pending]
            
            print(f"✅ Loaded {len(self.chain)} blocks from database")
            print(f"🪙 Total Supply: {self.total_supply:,} {TOKEN_SYMBOL}")

    def create_genesis_block(self):
        """Create and save genesis block with 1 Trillion ADT"""
        print("🚀 Creating genesis block with 1 Trillion ADT...")
        
        # Set initial supply
        self.genesis_supply = GENESIS_SUPPLY
        self.total_supply = GENESIS_SUPPLY
        self.circulating_supply = GENESIS_SUPPLY
        
        # Create genesis transaction
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
        
        # Save to database
        supabase_client.save_block(genesis_block.to_dict())
        
        # Create admin wallet with genesis supply
        supabase_client.create_wallet(
            "admin_wallet",
            "admin_private_key",
            "admin_public_key"
        )
        supabase_client.update_balance("admin_wallet", self.genesis_supply)
        
        # Create system wallets
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
                supabase_client.create_wallet(
                    wallet['address'],
                    wallet['private_key'],
                    wallet['public_key']
                )
                if wallet['balance'] > 0:
                    supabase_client.update_balance(wallet['address'], wallet['balance'])
                print(f"✅ Created wallet: {wallet['address']}")

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, transaction: Dict) -> None:
        # Add to pending
        self.pending_transactions.append(transaction)
        
        # Save to database
        tx_data = transaction.copy()
        tx_data['block_index'] = None
        supabase_client.save_transaction(tx_data)

    def mine_pending_transactions(self, mining_reward_address: str) -> None:
        if not self.pending_transactions:
            print("No pending transactions to mine")
            return
        
        # Check if mining reward would exceed max supply
        if self.total_supply + self.mining_reward > self.max_supply:
            print(f"⚠️ Cannot mine: Would exceed max supply of {self.max_supply:,}")
            return
        
        # Add mining reward transaction
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

        # Create new block
        block = Block(
            index=len(self.chain),
            transactions=self.pending_transactions,
            timestamp=time.time(),
            previous_hash=self.get_latest_block().hash
        )

        # Mine the block
        block.mine_block(self.difficulty)
        self.chain.append(block)
        
        # Save block to database
        block_dict = block.to_dict()
        supabase_client.save_block(block_dict)
        
        # Update transaction block indices
        for tx in self.pending_transactions:
            tx['block_index'] = block.index
            supabase_client.save_transaction(tx)
        
        # Update wallet balances
        for tx in self.pending_transactions:
            if tx['to']:
                wallet = supabase_client.get_wallet(tx['to'])
                if wallet:
                    supabase_client.update_balance(
                        tx['to'], 
                        wallet['balance'] + tx['amount']
                    )
            if tx['from'] != 'system' and tx['from'] != 'ad_system':
                wallet = supabase_client.get_wallet(tx['from'])
                if wallet:
                    supabase_client.update_balance(
                        tx['from'],
                        wallet['balance'] - tx['amount']
                    )
        
        self.pending_transactions = []
        print(f"✅ Block {block.index} mined! Total Supply: {self.total_supply:,} {TOKEN_SYMBOL}")

    def get_balance(self, address: str) -> float:
        """Get balance from database"""
        wallet = supabase_client.get_wallet(address)
        return wallet['balance'] if wallet else 0

    def validate_chain(self) -> bool:
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]

            if current_block.hash != current_block.calculate_hash():
                return False

            if current_block.previous_hash != previous_block.hash:
                return False

            if current_block.hash[:self.difficulty] != "0" * self.difficulty:
                return False

        return True

    def get_ad_reward(self, wallet_address: str) -> Dict:
        """Process ad viewing and reward the user"""
        # Check if wallet exists
        wallet = supabase_client.get_wallet(wallet_address)
        if not wallet:
            return {"status": "error", "message": "Wallet not found"}
        
        # Check if ad reward would exceed max supply
        if self.total_supply + self.ad_reward > self.max_supply:
            return {"status": "error", "message": "Max supply reached"}
        
        # Create reward transaction
        transaction = {
            "from": "ad_system",
            "to": wallet_address,
            "amount": self.ad_reward,
            "type": "ad_reward",
            "token": TOKEN_SYMBOL,
            "timestamp": time.time()
        }
        
        # Add transaction
        self.add_transaction(transaction)
        
        # Update supply
        self.total_supply += self.ad_reward
        self.circulating_supply += self.ad_reward
        
        # Save ad reward record
        supabase_client.save_ad_reward(wallet_address, self.ad_reward)
        
        # Auto-mine if enough transactions
        if len(self.pending_transactions) >= 3:
            self.mine_pending_transactions("system_reward")
        
        # Get updated balance
        new_balance = self.get_balance(wallet_address)
        
        return {
            "status": "success",
            "reward": self.ad_reward,
            "token": TOKEN_SYMBOL,
            "address": wallet_address,
            "new_balance": new_balance
        }

    def get_token_info(self) -> Dict:
        stats = supabase_client.get_blockchain_stats()
        return {
            "name": TOKEN_NAME,
            "symbol": TOKEN_SYMBOL,
            "decimals": TOKEN_DECIMALS,
            "total_supply": self.total_supply,
            "max_supply": self.max_supply,
            "genesis_supply": self.genesis_supply,
            "circulating_supply": stats['total_supply'],
            "mining_reward": self.mining_reward,
            "ad_reward": self.ad_reward,
            "difficulty": self.difficulty,
            "total_blocks": stats['total_blocks'],
            "total_wallets": stats['total_wallets'],
            "avg_block_time": stats.get('avg_block_time', 0)
        }

    def to_dict(self) -> Dict:
        return {
            "chain": [block.to_dict() for block in self.chain],
            "pending_transactions": self.pending_transactions,
            "difficulty": self.difficulty,
            "mining_reward": self.mining_reward,
            "ad_reward": self.ad_reward,
            "token_info": self.get_token_info()
        }

# Singleton instance
blockchain = Blockchain()
print(f"✅ Blockchain initialized with {len(blockchain.chain)} blocks")
print(f"🪙 Total Supply: {blockchain.total_supply:,} {TOKEN_SYMBOL}")
print(f"📊 Max Supply: {blockchain.max_supply:,} {TOKEN_SYMBOL}")
