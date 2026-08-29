import os
from supabase import create_client, Client
from datetime import datetime
import json
from dotenv import load_dotenv

load_dotenv()

class SupabaseClient:
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        self.client: Client = create_client(self.url, self.key)
        
        # Initialize tables if they don't exist
        self.init_tables()
    
    def init_tables(self):
        """Initialize database tables"""
        # Tables will be created via SQL migrations
        # But we'll ensure they exist
        
        # Create wallets table
        self.client.table('wallets').insert({
            'address': 'system',
            'balance': 0,
            'created_at': datetime.utcnow().isoformat()
        }).execute()
        
        print("✅ Supabase connected successfully")
    
    # Wallet Operations
    def create_wallet(self, address: str, private_key: str, public_key: str):
        """Create a new wallet in database"""
        data = {
            'address': address,
            'private_key': private_key,
            'public_key': public_key,
            'balance': 0,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        result = self.client.table('wallets').insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_wallet(self, address: str):
        """Get wallet by address"""
        result = self.client.table('wallets')\
            .select('*')\
            .eq('address', address)\
            .execute()
        return result.data[0] if result.data else None
    
    def update_balance(self, address: str, balance: float):
        """Update wallet balance"""
        data = {
            'balance': balance,
            'updated_at': datetime.utcnow().isoformat()
        }
        result = self.client.table('wallets')\
            .update(data)\
            .eq('address', address)\
            .execute()
        return result.data[0] if result.data else None
    
    def get_all_wallets(self, limit: int = 100):
        """Get all wallets with their balances"""
        result = self.client.table('wallets')\
            .select('address, balance, created_at')\
            .order('balance', desc=True)\
            .limit(limit)\
            .execute()
        return result.data
    
    # Block Operations
    def save_block(self, block_data: dict):
        """Save a block to database"""
        data = {
            'index': block_data['index'],
            'hash': block_data['hash'],
            'previous_hash': block_data['previous_hash'],
            'timestamp': datetime.fromtimestamp(block_data['timestamp']).isoformat(),
            'transactions': json.dumps(block_data['transactions']),
            'nonce': block_data['nonce'],
            'created_at': datetime.utcnow().isoformat()
        }
        result = self.client.table('blocks').insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_latest_block(self):
        """Get the latest block"""
        result = self.client.table('blocks')\
            .select('*')\
            .order('index', desc=True)\
            .limit(1)\
            .execute()
        return result.data[0] if result.data else None
    
    def get_block_by_index(self, index: int):
        """Get block by index"""
        result = self.client.table('blocks')\
            .select('*')\
            .eq('index', index)\
            .execute()
        return result.data[0] if result.data else None
    
    def get_all_blocks(self, limit: int = 100):
        """Get all blocks"""
        result = self.client.table('blocks')\
            .select('*')\
            .order('index', desc=True)\
            .limit(limit)\
            .execute()
        return result.data
    
    # Transaction Operations
    def save_transaction(self, transaction: dict):
        """Save a transaction to database"""
        data = {
            'tx_hash': self.generate_tx_hash(transaction),
            'from_address': transaction['from'],
            'to_address': transaction['to'],
            'amount': transaction['amount'],
            'token': transaction.get('token', 'ADT'),
            'type': transaction.get('type', 'transfer'),
            'block_index': transaction.get('block_index', None),
            'timestamp': datetime.fromtimestamp(transaction['timestamp']).isoformat(),
            'data': json.dumps(transaction),
            'created_at': datetime.utcnow().isoformat()
        }
        result = self.client.table('transactions').insert(data).execute()
        return result.data[0] if result.data else None
    
    def generate_tx_hash(self, transaction: dict) -> str:
        """Generate transaction hash"""
        import hashlib
        tx_string = f"{transaction['from']}{transaction['to']}{transaction['amount']}{transaction['timestamp']}"
        return hashlib.sha256(tx_string.encode()).hexdigest()[:16]
    
    def get_transactions_by_address(self, address: str, limit: int = 50):
        """Get all transactions for an address"""
        result = self.client.table('transactions')\
            .select('*')\
            .or_(f'from_address.eq.{address},to_address.eq.{address}')\
            .order('timestamp', desc=True)\
            .limit(limit)\
            .execute()
        return result.data
    
    def get_pending_transactions(self, limit: int = 50):
        """Get pending transactions (not in a block yet)"""
        result = self.client.table('transactions')\
            .select('*')\
            .is_('block_index', 'null')\
            .order('timestamp', asc=True)\
            .limit(limit)\
            .execute()
        return result.data
    
    # Ad Reward Operations
    def save_ad_reward(self, wallet_address: str, reward: float):
        """Save ad reward record"""
        data = {
            'wallet_address': wallet_address,
            'reward_amount': reward,
            'timestamp': datetime.utcnow().isoformat(),
            'created_at': datetime.utcnow().isoformat()
        }
        result = self.client.table('ad_rewards').insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_ad_rewards_by_address(self, address: str, limit: int = 100):
        """Get ad rewards for an address"""
        result = self.client.table('ad_rewards')\
            .select('*')\
            .eq('wallet_address', address)\
            .order('timestamp', desc=True)\
            .limit(limit)\
            .execute()
        return result.data
    
    def get_total_ad_rewards(self, address: str):
        """Get total ad rewards for an address"""
        result = self.client.table('ad_rewards')\
            .select('reward_amount')\
            .eq('wallet_address', address)\
            .execute()
        total = sum([r['reward_amount'] for r in result.data])
        return total
    
    # Statistics
    def get_blockchain_stats(self):
        """Get blockchain statistics"""
        # Total blocks
        blocks_result = self.client.table('blocks').select('count').execute()
        total_blocks = blocks_result.count
        
        # Total transactions
        tx_result = self.client.table('transactions').select('count').execute()
        total_transactions = tx_result.count
        
        # Total wallets
        wallets_result = self.client.table('wallets').select('count').execute()
        total_wallets = wallets_result.count
        
        # Total ADT in circulation
        balance_result = self.client.table('wallets')\
            .select('balance')\
            .execute()
        total_supply = sum([w['balance'] for w in balance_result.data])
        
        # Average block time (if more than 1 block)
        avg_block_time = 0
        if total_blocks > 1:
            latest = self.get_latest_block()
            first = self.get_block_by_index(0)
            if latest and first:
                latest_time = datetime.fromisoformat(latest['timestamp'].replace('Z', '+00:00'))
                first_time = datetime.fromisoformat(first['timestamp'].replace('Z', '+00:00'))
                time_diff = (latest_time - first_time).total_seconds()
                avg_block_time = time_diff / (total_blocks - 1)
        
        return {
            'total_blocks': total_blocks,
            'total_transactions': total_transactions,
            'total_wallets': total_wallets,
            'total_supply': total_supply,
            'avg_block_time': avg_block_time,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    # Real-time subscriptions
    def subscribe_to_transactions(self, callback):
        """Subscribe to new transactions in real-time"""
        def handle_change(payload):
            callback(payload)
        
        channel = self.client.channel('transaction_updates')
        channel.on_postgres_changes(
            'INSERT',
            schema='public',
            table='transactions',
            callback=handle_change
        )
        channel.subscribe()
        return channel
    
    def subscribe_to_blocks(self, callback):
        """Subscribe to new blocks in real-time"""
        def handle_change(payload):
            callback(payload)
        
        channel = self.client.channel('block_updates')
        channel.on_postgres_changes(
            'INSERT',
            schema='public',
            table='blocks',
            callback=handle_change
        )
        channel.subscribe()
        return channel

# Singleton instance
supabase_client = SupabaseClient()
