import hashlib
import json
import time
from typing import List, Dict, Any
from datetime import datetime
from supabase_client import supabase_client

# Token Configuration
TOKEN_SYMBOL = "ADT"
TOKEN_NAME = "Ad Token"
TOKEN_DECIMALS = 18
TOTAL_SUPPLY = 100_000_000  # 100 Million ADT

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
        self.difficulty = 4
        self.mining_reward = 10
        self.ad_reward = 0.5
        self.token_symbol = TOKEN_SYMBOL
        self.token_name = TOKEN_NAME
        self.total_supply = TOTAL_SUPPLY
        
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

    def create_genesis_block(self):
        """Create and save genesis block"""
        genesis_block = Block(0, [], time.time(), "0")
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
        
        # Save to database
        supabase_client.save_block(genesis_block.to_dict())
        print("✅ Genesis block created and saved to database")

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
            "total_supply": TOTAL_SUPPLY,
            "circulating_supply": stats['total_supply'],
            "mining_reward": self.mining_reward,
            "ad_reward": self.ad_reward,
            "total_blocks": stats['total_blocks'],
            "total_wallets": stats['total_wallets'],
            "avg_block_time": stats['avg_block_time']
        }

    def to_dict(self) -> Dict:
        return {
            "chain": [block.to_dict() for block in self.chain],
            "pending_transactions": self.pending_transactions,
            "difficulty": self.difficulty,
            "token_info": self.get_token_info()
        }

# Singleton instance
blockchain = Blockchain()
