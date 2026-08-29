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
        self.service_role = os.getenv('SUPABASE_SERVICE_ROLE')
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        # Use service role for backend operations if available
        key_to_use = self.service_role if self.service_role else self.key
        self.client: Client = create_client(self.url, key_to_use)
        
        print(f"✅ Supabase client initialized")
        print(f"📡 URL: {self.url}")
        
        # Don't auto-initialize tables to avoid errors
        # self.init_tables()
    
    def init_tables(self):
        """Initialize database tables - called manually if needed"""
        try:
            # Check if wallets table exists by trying to insert a test record
            # This will fail if table doesn't exist, which is fine
            pass
        except Exception as e:
            print(f"⚠️ Tables may need to be created: {e}")
    
    def get_all_wallets(self, limit=100):
        """Get all wallets with balances"""
        try:
            result = self.client.table('wallets')\
                .select('*')\
                .order('balance', desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting wallets: {e}")
            return []

    def create_wallet(self, address, private_key, public_key):
        """Create new wallet with proper values"""
        try:
            # Check if wallet already exists
            existing = self.get_wallet(address)
            if existing:
                print(f"ℹ️ Wallet {address} already exists")
                return existing
            
            data = {
                'address': address,
                'private_key': private_key,  # Must NOT be null
                'public_key': public_key,    # Must NOT be null
                'balance': 0,
                'total_ads_watched': 0,
                'total_ad_rewards': 0,
                'total_mining_sessions': 0,
                'mining_active': False,
                'mining_accumulated': 0,
                'total_mined': 0,
                'app_version': '1.0.0',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            result = self.client.table('wallets').insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error creating wallet: {e}")
            return None

    def get_wallet(self, address):
        """Get wallet by address"""
        try:
            result = self.client.table('wallets')\
                .select('*')\
                .eq('address', address)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error getting wallet: {e}")
            return None

    def update_balance(self, address, balance):
        """Update wallet balance"""
        try:
            data = {
                'balance': float(balance),
                'updated_at': datetime.utcnow().isoformat()
            }
            result = self.client.table('wallets')\
                .update(data)\
                .eq('address', address)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error updating balance: {e}")
            return None

    def update_mining_status(self, address, active, started_at=None, balance=None, total_mined=None):
        """Update mining status for a wallet"""
        try:
            data = {
                'mining_active': active,
                'updated_at': datetime.utcnow().isoformat()
            }
            if started_at:
                data['mining_started'] = started_at
            if balance is not None:
                data['balance'] = float(balance)
            if total_mined is not None:
                data['total_mined'] = float(total_mined)
            
            result = self.client.table('wallets')\
                .update(data)\
                .eq('address', address)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error updating mining status: {e}")
            return None

    def save_block(self, block_data):
        """Save block to database"""
        try:
            data = {
                'index': block_data['index'],
                'hash': block_data['hash'],
                'previous_hash': block_data['previous_hash'],
                'timestamp': datetime.fromtimestamp(block_data['timestamp']).isoformat(),
                'transactions': json.dumps(block_data['transactions']),
                'nonce': block_data['nonce']
            }
            result = self.client.table('blocks').insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error saving block: {e}")
            return None

    def get_latest_block(self):
        """Get latest block"""
        try:
            result = self.client.table('blocks')\
                .select('*')\
                .order('index', desc=True)\
                .limit(1)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error getting latest block: {e}")
            return None

    def get_all_blocks(self, limit=1000):
        """Get all blocks"""
        try:
            result = self.client.table('blocks')\
                .select('*')\
                .order('index', asc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting blocks: {e}")
            return []

    def save_transaction(self, transaction):
        """Save transaction to database"""
        try:
            tx_hash = self.generate_tx_hash(transaction)
            data = {
                'tx_hash': tx_hash,
                'from_address': transaction.get('from', 'system'),
                'to_address': transaction.get('to', 'system'),
                'amount': float(transaction.get('amount', 0)),
                'token': transaction.get('token', 'ADT'),
                'type': transaction.get('type', 'transfer'),
                'block_index': transaction.get('block_index', None),
                'timestamp': datetime.fromtimestamp(transaction.get('timestamp', time.time())).isoformat(),
                'data': json.dumps(transaction)
            }
            result = self.client.table('transactions').insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error saving transaction: {e}")
            return None

    def generate_tx_hash(self, transaction):
        """Generate transaction hash"""
        import hashlib
        tx_string = f"{transaction.get('from', '')}{transaction.get('to', '')}{transaction.get('amount', 0)}{transaction.get('timestamp', time.time())}"
        return hashlib.sha256(tx_string.encode()).hexdigest()

    def get_pending_transactions(self, limit=50):
        """Get pending transactions"""
        try:
            result = self.client.table('transactions')\
                .select('*')\
                .is_('block_index', 'null')\
                .order('timestamp', asc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting pending transactions: {e}")
            return []

    def save_ad_reward(self, wallet_address, reward_amount):
        """Save ad reward record"""
        try:
            data = {
                'wallet_address': wallet_address,
                'reward_amount': float(reward_amount),
                'timestamp': datetime.utcnow().isoformat()
            }
            result = self.client.table('ad_rewards').insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error saving ad reward: {e}")
            return None

    def get_blockchain_stats(self):
        """Get blockchain statistics"""
        try:
            # Get counts
            blocks = self.client.table('blocks').select('*', count='exact').execute()
            txs = self.client.table('transactions').select('*', count='exact').execute()
            wallets = self.client.table('wallets').select('*', count='exact').execute()
            
            # Get total supply from wallets
            wallet_data = self.client.table('wallets').select('balance').execute()
            total_supply = sum([w['balance'] for w in wallet_data.data]) if wallet_data.data else 0
            
            return {
                'total_blocks': blocks.count if hasattr(blocks, 'count') else 0,
                'total_transactions': txs.count if hasattr(txs, 'count') else 0,
                'total_wallets': wallets.count if hasattr(wallets, 'count') else 0,
                'total_supply': total_supply,
                'avg_block_time': 0
            }
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {
                'total_blocks': 0,
                'total_transactions': 0,
                'total_wallets': 0,
                'total_supply': 0,
                'avg_block_time': 0
            }

# Import time for generate_tx_hash
import time

# Initialize client
supabase_client = SupabaseClient()
