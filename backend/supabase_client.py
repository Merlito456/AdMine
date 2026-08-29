import os
import time
import hashlib
import json
from supabase import create_client, Client
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

class SupabaseClient:
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        self.service_role = os.getenv('SUPABASE_SERVICE_ROLE')
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        key_to_use = self.service_role if self.service_role else self.key
        self.client: Client = create_client(self.url, key_to_use)
        
        print(f"✅ Supabase client initialized")
        print(f"📡 URL: {self.url}")

    # ============================================
    # WALLET OPERATIONS
    # ============================================

    def create_wallet(self, address, private_key, public_key):
        """Create new wallet"""
        try:
            existing = self.get_wallet(address)
            if existing:
                return existing
            
            data = {
                'address': address,
                'private_key': private_key,
                'public_key': public_key,
                'balance': 0,
                'total_ads_watched': 0,
                'total_ad_rewards': 0,
                'total_mining_sessions': 0,
                'mining_active': False,
                'mining_accumulated': 0,
                'total_mined': 0,
                'app_version': '1.0.0',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
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

    def update_wallet(self, address, data):
        """Update wallet data"""
        try:
            result = self.client.table('wallets')\
                .update(data)\
                .eq('address', address)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error updating wallet: {e}")
            return None

    def update_balance(self, address, balance):
        """Update wallet balance"""
        try:
            data = {'balance': float(balance), 'updated_at': datetime.now(timezone.utc).isoformat()}
            return self.update_wallet(address, data)
        except Exception as e:
            print(f"❌ Error updating balance: {e}")
            return None

    def update_mining_status(self, address, active, started_at=None, balance=None, total_mined=None):
        """Update mining status"""
        try:
            data = {
                'mining_active': active,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            if started_at:
                data['mining_started'] = started_at
            if balance is not None:
                data['balance'] = float(balance)
            if total_mined is not None:
                data['total_mined'] = float(total_mined)
            
            return self.update_wallet(address, data)
        except Exception as e:
            print(f"❌ Error updating mining status: {e}")
            return None

    def get_all_wallets(self, limit=100):
        """Get all wallets"""
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

    # ============================================
    # BLOCK OPERATIONS
    # ============================================

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
        """Get all blocks - FIXED: removed 'asc' parameter"""
        try:
            result = self.client.table('blocks')\
                .select('*')\
                .order('index')\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting blocks: {e}")
            return []

    # ============================================
    # TRANSACTION OPERATIONS
    # ============================================

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

    def get_transactions(self, address, limit=50):
        """Get transactions for a wallet"""
        try:
            result = self.client.table('transactions')\
                .select('*')\
                .or_(f'from_address.eq.{address},to_address.eq.{address}')\
                .order('timestamp', desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting transactions: {e}")
            return []

    def get_pending_transactions(self, limit=50):
        """Get pending transactions - FIXED: removed 'asc' parameter"""
        try:
            result = self.client.table('transactions')\
                .select('*')\
                .is_('block_index', 'null')\
                .order('timestamp')\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting pending transactions: {e}")
            return []

    # ============================================
    # AD REWARD OPERATIONS
    # ============================================

    def save_ad_reward(self, wallet_address, reward_amount, ad_type='rewarded', ad_unit_id=''):
        """Save ad reward record"""
        try:
            data = {
                'wallet_address': wallet_address,
                'reward_amount': float(reward_amount),
                'ad_type': ad_type,
                'ad_unit_id': ad_unit_id,
                'reward_claimed': True,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            result = self.client.table('ad_rewards').insert(data).execute()
            
            # Also record in watch history
            history_data = {
                'wallet_address': wallet_address,
                'ad_type': ad_type,
                'ad_unit_id': ad_unit_id,
                'reward_amount': float(reward_amount),
                'reward_claimed': True,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            self.client.table('ad_watch_history').insert(history_data).execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error saving ad reward: {e}")
            return None

    def get_ad_history(self, address, limit=50):
        """Get ad watching history for a wallet"""
        try:
            result = self.client.table('ad_watch_history')\
                .select('*')\
                .eq('wallet_address', address)\
                .order('timestamp', desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting ad history: {e}")
            return []

    def get_ad_stats(self):
        """Get global ad statistics"""
        try:
            # Total ad views
            views = self.client.table('ad_watch_history').select('*', count='exact').execute()
            
            # Total rewards
            rewards = self.client.table('ad_watch_history')\
                .select('reward_amount')\
                .execute()
            total_rewards = sum([r['reward_amount'] for r in rewards.data]) if rewards.data else 0
            
            return {
                'total_ad_views': views.count if hasattr(views, 'count') else 0,
                'total_ad_rewards': total_rewards
            }
        except Exception as e:
            print(f"❌ Error getting ad stats: {e}")
            return {'total_ad_views': 0, 'total_ad_rewards': 0}

    # ============================================
    # MINING SESSION OPERATIONS - COMPLETE
    # ============================================

    def create_mining_session(self, session_data):
        """Create a new mining session"""
        try:
            # Ensure required fields
            required = ['wallet_address', 'start_time', 'status']
            for field in required:
                if field not in session_data:
                    session_data[field] = 'active' if field == 'status' else None
            
            # Set defaults if not provided
            if 'reward_amount' not in session_data:
                session_data['reward_amount'] = 0
            if 'reward_earned' not in session_data:
                session_data['reward_earned'] = 0
            if 'duration_seconds' not in session_data:
                session_data['duration_seconds'] = 0
            if 'hourly_rate' not in session_data:
                session_data['hourly_rate'] = 0.5
            
            result = self.client.table('mining_sessions').insert(session_data).execute()
            if result.data:
                print(f"✅ Mining session created: {result.data[0]['id']}")
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error creating mining session: {e}")
            return None

    def get_active_mining_session(self, address):
        """Get active mining session for a wallet"""
        try:
            result = self.client.table('mining_sessions')\
                .select('*')\
                .eq('wallet_address', address)\
                .eq('status', 'active')\
                .order('start_time', desc=True)\
                .limit(1)\
                .execute()
            if result.data:
                print(f"✅ Found active session for {address}: {result.data[0]['id']}")
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error getting active mining session: {e}")
            return None

    def update_mining_session(self, session_id, end_time, status, reward_earned, duration_seconds):
        """Update a mining session"""
        try:
            data = {
                'end_time': end_time,
                'status': status,
                'reward_earned': float(reward_earned),
                'reward_amount': float(reward_earned),
                'duration_seconds': duration_seconds
            }
            result = self.client.table('mining_sessions')\
                .update(data)\
                .eq('id', session_id)\
                .execute()
            if result.data:
                print(f"✅ Mining session updated: {result.data[0]['id']}")
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error updating mining session: {e}")
            return None

    def get_mining_sessions(self, address, limit=50):
        """Get mining sessions for a wallet"""
        try:
            result = self.client.table('mining_sessions')\
                .select('*')\
                .eq('wallet_address', address)\
                .order('start_time', desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting mining sessions: {e}")
            return []

    def get_mining_stats(self, address):
        """Get mining statistics for a wallet"""
        try:
            wallet = self.get_wallet(address)
            if not wallet:
                return None
            
            sessions = self.get_mining_sessions(address)
            total_earned = sum([s.get('reward_earned', 0) for s in sessions]) if sessions else 0
            
            return {
                'address': address,
                'total_mined': wallet.get('total_mined', 0),
                'balance': wallet.get('balance', 0),
                'mining_active': wallet.get('mining_active', False),
                'total_sessions': len(sessions),
                'total_earned': total_earned,
                'hourly_rate': wallet.get('hourly_rate', 0.5) if wallet else 0.5,
                'daily_cap': 12.0
            }
        except Exception as e:
            print(f"❌ Error getting mining stats: {e}")
            return None

    # ============================================
    # REFERRAL OPERATIONS - COMPLETE
    # ============================================

    def get_wallet_by_referral_code(self, code):
        """Get wallet by referral code"""
        try:
            result = self.client.table('wallets')\
                .select('*')\
                .eq('referral_code', code)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error getting wallet by referral code: {e}")
            return None

    def get_referral_by_referred(self, address):
        """Get referral by referred address"""
        try:
            result = self.client.table('referrals')\
                .select('*')\
                .eq('referred_address', address)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error getting referral by referred: {e}")
            return None

    def create_referral(self, referral_data):
        """Create a new referral"""
        try:
            result = self.client.table('referrals').insert(referral_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error creating referral: {e}")
            return None

    def create_referral_reward(self, reward_data):
        """Create a referral reward record"""
        try:
            result = self.client.table('referral_rewards').insert(reward_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error creating referral reward: {e}")
            return None

    def get_referral_stats(self, address):
        """Get referral statistics"""
        try:
            result = self.client.table('referral_stats')\
                .select('*')\
                .eq('referrer_address', address)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error getting referral stats: {e}")
            return None

    def get_referrals_by_referrer(self, address, limit=50):
        """Get referrals by referrer"""
        try:
            result = self.client.table('referrals')\
                .select('*')\
                .eq('referrer_address', address)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting referrals by referrer: {e}")
            return []

    def get_referral_rewards(self, address, limit=50):
        """Get referral rewards for a wallet"""
        try:
            result = self.client.table('referral_rewards')\
                .select('*')\
                .eq('referrer_address', address)\
                .order('timestamp', desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting referral rewards: {e}")
            return []

    # ============================================
    # GAME REWARD OPERATIONS
    # ============================================

    def update_wallet_stats(self, address, total_games_played=0, total_games_won=0, 
                            total_game_rewards=0, last_game_played=None):
        """Update wallet game statistics"""
        try:
            # Get current wallet
            wallet = self.get_wallet(address)
            if not wallet:
                return None
            
            data = {
                'total_games_played': wallet.get('total_games_played', 0) + total_games_played,
                'total_games_won': wallet.get('total_games_won', 0) + total_games_won,
                'total_game_rewards': wallet.get('total_game_rewards', 0) + total_game_rewards,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            if last_game_played:
                data['last_game_played'] = last_game_played
                
            return self.update_wallet(address, data)
        except Exception as e:
            print(f"❌ Error updating wallet stats: {e}")
            return None

    def save_game_history(self, game_record):
        """Save game history record"""
        try:
            result = self.client.table('game_history').insert(game_record).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error saving game history: {e}")
            return None

    def get_game_history(self, address, limit=50):
        """Get game history for a wallet"""
        try:
            result = self.client.table('game_history')\
                .select('*')\
                .eq('wallet_address', address)\
                .order('timestamp', desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting game history: {e}")
            return []

    def get_game_stats(self, address):
        """Get game statistics for a wallet"""
        try:
            wallet = self.get_wallet(address)
            if not wallet:
                return None
                
            # Get game-specific stats
            games = self.client.table('game_history')\
                .select('game_name, count, sum(reward_amount)')\
                .eq('wallet_address', address)\
                .group_by('game_name')\
                .execute()
            
            return {
                'total_games_played': wallet.get('total_games_played', 0),
                'total_games_won': wallet.get('total_games_won', 0),
                'total_game_rewards': wallet.get('total_game_rewards', 0),
                'last_game_played': wallet.get('last_game_played'),
                'games': games.data if hasattr(games, 'data') else [],
                'balance': wallet.get('balance', 0)
            }
        except Exception as e:
            print(f"❌ Error getting game stats: {e}")
            return None

    def get_game_leaderboard(self, game_name, limit=20):
        """Get leaderboard for a specific game"""
        try:
            result = self.client.table('game_history')\
                .select('wallet_address, sum(reward_amount) as total_rewards, count as plays')\
                .eq('game_name', game_name)\
                .group_by('wallet_address')\
                .order('total_rewards', desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting game leaderboard: {e}")
            return []

    def get_game_leaderboard_all(self, limit=20):
        """Get overall game leaderboard"""
        try:
            result = self.client.table('game_history')\
                .select('wallet_address, sum(reward_amount) as total_rewards, count as total_games')\
                .group_by('wallet_address')\
                .order('total_rewards', desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting overall leaderboard: {e}")
            return []

    # ============================================
    # ANALYTICS OPERATIONS
    # ============================================

    def track_analytics(self, wallet_address, session_id, screen_name, action_type, action_data=None):
        """Track user analytics"""
        try:
            data = {
                'wallet_address': wallet_address,
                'session_id': session_id,
                'screen_name': screen_name,
                'action_type': action_type,
                'action_data': action_data or {},
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            result = self.client.table('app_analytics').insert(data).execute()
            
            # Update last active
            self.update_wallet(wallet_address, {
                'last_active': datetime.now(timezone.utc).isoformat()
            })
            
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error tracking analytics: {e}")
            return None

    def get_user_analytics(self, address, limit=50):
        """Get user analytics"""
        try:
            result = self.client.table('app_analytics')\
                .select('*')\
                .eq('wallet_address', address)\
                .order('timestamp', desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"❌ Error getting user analytics: {e}")
            return []

    # ============================================
    # CONFIG OPERATIONS
    # ============================================

    def get_config(self, key):
        """Get configuration value"""
        try:
            result = self.client.table('config')\
                .select('value')\
                .eq('key', key)\
                .execute()
            return result.data[0]['value'] if result.data else None
        except Exception as e:
            print(f"❌ Error getting config: {e}")
            return None

    def set_config(self, key, value):
        """Set configuration value"""
        try:
            data = {
                'key': key,
                'value': json.dumps(value) if isinstance(value, dict) else str(value),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            # Check if exists
            existing = self.client.table('config').select('*').eq('key', key).execute()
            if existing.data:
                result = self.client.table('config')\
                    .update(data)\
                    .eq('key', key)\
                    .execute()
            else:
                data['created_at'] = datetime.now(timezone.utc).isoformat()
                result = self.client.table('config').insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error setting config: {e}")
            return None

    # ============================================
    # STATS OPERATIONS
    # ============================================

    def get_blockchain_stats(self):
        """Get blockchain statistics"""
        try:
            # Get counts
            blocks = self.client.table('blocks').select('*', count='exact').execute()
            txs = self.client.table('transactions').select('*', count='exact').execute()
            wallets = self.client.table('wallets').select('*', count='exact').execute()
            
            # Get total supply
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

    def get_user_stats(self, address):
        """Get user statistics from view"""
        try:
            result = self.client.table('user_stats')\
                .select('*')\
                .eq('address', address)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error getting user stats: {e}")
            return None

# Initialize client
supabase_client = SupabaseClient()
print("✅ Supabase client ready")
