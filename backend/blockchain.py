import hashlib
import json
import time
from typing import List, Dict, Any
from datetime import datetime
import requests

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

class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]
        self.difficulty = 4
        self.pending_transactions = []
        self.mining_reward = 10
        self.ad_reward = 0.5
        self.wallets = {}

    def create_genesis_block(self) -> Block:
        return Block(0, [], time.time(), "0")

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, transaction: Dict) -> None:
        self.pending_transactions.append(transaction)

    def mine_pending_transactions(self, mining_reward_address: str) -> None:
        # Add mining reward transaction
        reward_tx = {
            "from": "system",
            "to": mining_reward_address,
            "amount": self.mining_reward,
            "type": "mining_reward",
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
        self.pending_transactions = []

    def get_balance(self, address: str) -> float:
        balance = 0
        for block in self.chain:
            for tx in block.transactions:
                if tx["to"] == address:
                    balance += tx["amount"]
                if tx["from"] == address:
                    balance -= tx["amount"]
        return balance

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
        transaction = {
            "from": "ad_system",
            "to": wallet_address,
            "amount": self.ad_reward,
            "type": "ad_reward",
            "timestamp": time.time()
        }
        self.add_transaction(transaction)
        
        # Auto-mine if enough transactions
        if len(self.pending_transactions) >= 3:
            self.mine_pending_transactions("system_reward")
        
        return {
            "status": "success",
            "reward": self.ad_reward,
            "address": wallet_address,
            "new_balance": self.get_balance(wallet_address)
        }

    def to_dict(self) -> Dict:
        return {
            "chain": [{
                "index": block.index,
                "transactions": block.transactions,
                "timestamp": block.timestamp,
                "previous_hash": block.previous_hash,
                "hash": block.hash,
                "nonce": block.nonce
            } for block in self.chain],
            "pending_transactions": self.pending_transactions,
            "difficulty": self.difficulty,
            "mining_reward": self.mining_reward,
            "ad_reward": self.ad_reward
        }

# Singleton instance
blockchain = Blockchain()
