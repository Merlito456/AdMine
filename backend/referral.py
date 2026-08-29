# backend/referral.py
import os
import time
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from supabase_client import supabase_client
from dotenv import load_dotenv

load_dotenv()

# ============================================
# REFERRAL CONFIG
# ============================================
REFERRAL_LEVEL1_PERCENT = 5.0   # 5% for direct referrals
REFERRAL_LEVEL2_PERCENT = 2.0   # 2% for second-level referrals
REFERRAL_REWARD_INTERVAL = 24   # 24 hours

# ============================================
# REFERRAL CODE GENERATION
# ============================================

def generate_referral_code():
    """Generate a unique referral code"""
    import random
    import string
    # Generate 8 character alphanumeric code
    chars = string.ascii_uppercase + string.digits
    code = ''.join(random.choices(chars, k=8))
    return code

def create_referral_code(address):
    """Create a referral code for a wallet"""
    try:
        # Check if code already exists
        wallet = supabase_client.get_wallet(address)
        if not wallet:
            return {'error': 'Wallet not found'}, 404
        
        if wallet.get('referral_code'):
            return {'referral_code': wallet['referral_code']}, 200
        
        # Generate unique code
        code = generate_referral_code()
        attempts = 0
        while attempts < 10:
            existing = supabase_client.get_wallet_by_referral_code(code)
            if not existing:
                break
            code = generate_referral_code()
            attempts += 1
        
        # Save code
        supabase_client.update_wallet(address, {'referral_code': code})
        
        return {'referral_code': code, 'address': address}, 200
    except Exception as e:
        return {'error': str(e)}, 500

# ============================================
# REFERRAL LINK MANAGEMENT
# ============================================

def process_referral(referrer_code, new_address):
    """Process a new referral"""
    try:
        # Find referrer by code
        referrer = supabase_client.get_wallet_by_referral_code(referrer_code)
        if not referrer:
            return {'error': 'Invalid referral code'}, 404
        
        if referrer['address'] == new_address:
            return {'error': 'Cannot refer yourself'}, 400
        
        # Check if already referred
        existing = supabase_client.get_referral_by_referred(new_address)
        if existing:
            return {'error': 'Already referred by someone else'}, 400
        
        # Create referral record
        referral_data = {
            'referrer_address': referrer['address'],
            'referred_address': new_address,
            'level': 1,
            'status': 'active'
        }
        result = supabase_client.create_referral(referral_data)
        
        if result:
            # Update referrer's referral count
            supabase_client.update_wallet(referrer['address'], {
                'referral_count': supabase_client.get_wallet(referrer['address'])['referral_count'] + 1,
                'referred_by': new_address
            })
            
            return {
                'status': 'success',
                'message': 'Referral recorded successfully!',
                'referrer': referrer['address'],
                'referred': new_address
            }, 200
        
        return {'error': 'Failed to create referral'}, 500
    except Exception as e:
        return {'error': str(e)}, 500

# ============================================
# REFERRAL REWARD CALCULATION
# ============================================

def calculate_referral_rewards(miner_address, mining_reward):
    """Calculate and distribute referral rewards"""
    try:
        # Find who referred this miner
        referral = supabase_client.get_referral_by_referred(miner_address)
        if not referral:
            return
        
        rewards_distributed = []
        
        # Level 1: Direct referrer gets 5%
        if referral['level'] == 1:
            level1_reward = mining_reward * (REFERRAL_LEVEL1_PERCENT / 100)
            if level1_reward > 0:
                # Distribute to level 1 referrer
                reward_data = {
                    'referrer_address': referral['referrer_address'],
                    'miner_address': miner_address,
                    'referral_id': referral['id'],
                    'reward_amount': level1_reward,
                    'reward_percentage': REFERRAL_LEVEL1_PERCENT,
                    'source_type': 'mining',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                supabase_client.create_referral_reward(reward_data)
                
                # Update referrer's balance
                supabase_client.update_balance(
                    referral['referrer_address'],
                    supabase_client.get_balance(referral['referrer_address']) + level1_reward
                )
                
                rewards_distributed.append({
                    'address': referral['referrer_address'],
                    'amount': level1_reward,
                    'level': 1,
                    'percentage': REFERRAL_LEVEL1_PERCENT
                })
                
                # Check for level 2 referral (referrer's referrer)
                level2_referral = supabase_client.get_referral_by_referred(referral['referrer_address'])
                if level2_referral:
                    level2_reward = mining_reward * (REFERRAL_LEVEL2_PERCENT / 100)
                    if level2_reward > 0:
                        # Distribute to level 2 referrer
                        reward_data_2 = {
                            'referrer_address': level2_referral['referrer_address'],
                            'miner_address': miner_address,
                            'referral_id': level2_referral['id'],
                            'reward_amount': level2_reward,
                            'reward_percentage': REFERRAL_LEVEL2_PERCENT,
                            'source_type': 'mining',
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                        supabase_client.create_referral_reward(reward_data_2)
                        
                        # Update level 2 referrer's balance
                        supabase_client.update_balance(
                            level2_referral['referrer_address'],
                            supabase_client.get_balance(level2_referral['referrer_address']) + level2_reward
                        )
                        
                        rewards_distributed.append({
                            'address': level2_referral['referrer_address'],
                            'amount': level2_reward,
                            'level': 2,
                            'percentage': REFERRAL_LEVEL2_PERCENT
                        })
        
        return rewards_distributed
    except Exception as e:
        print(f"❌ Error calculating referral rewards: {e}")
        return None

def get_referral_stats(address):
    """Get referral statistics for a wallet"""
    try:
        stats = supabase_client.get_referral_stats(address)
        if stats:
            return stats
        return {
            'total_referrals': 0,
            'level1_count': 0,
            'level2_count': 0,
            'total_rewards_earned': 0,
            'mining_rewards': 0,
            'ad_rewards': 0,
            'level1_rewards': 0,
            'level2_rewards': 0
        }
    except Exception as e:
        return {'error': str(e)}

def get_referral_tree(address, depth=3):
    """Get referral tree for a wallet"""
    try:
        tree = []
        referrals = supabase_client.get_referrals_by_referrer(address)
        for ref in referrals[:10]:  # Limit to 10 per level
            node = {
                'address': ref['referred_address'],
                'level': ref['level'],
                'created_at': ref['created_at'],
                'reward_earned': ref.get('reward_earned', 0)
            }
            # Get sub-referrals
            if depth > 1:
                sub_tree = get_referral_tree(ref['referred_address'], depth - 1)
                if sub_tree:
                    node['children'] = sub_tree
            tree.append(node)
        return tree
    except Exception as e:
        return []
