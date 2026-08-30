# backend/auth.py
import os
import json
import time
import hashlib
import secrets
import random
import string
from datetime import datetime, timezone, timedelta
from flask import request, jsonify, session
from functools import wraps
from supabase import create_client
from dotenv import load_dotenv
import jwt

load_dotenv()

# ============================================
# CONFIGURATION
# ============================================
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://mydbvqyxoxqzluslpavh.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'sb_publishable_7An_A_PQbrrTzpyrSKOEgw_dPf5mj_o')
# Service role key - bypasses all RLS policies
SUPABASE_SERVICE_ROLE = os.getenv('SUPABASE_SERVICE_ROLE', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im15ZGJ2cXl4b3hxemx1c2xwYXZoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4Nzk5MTA2MCwiZXhwIjoyMTAzNTY3MDYwfQ.fEwC1A72dyadslnC8x6JFBLGiVriRVNCCQA3244sVQw')
JWT_SECRET = os.getenv('JWT_SECRET', secrets.token_hex(32))
JWT_EXPIRATION = 3600 * 24 * 7  # 7 days

# Initialize Supabase client with SERVICE ROLE (bypasses RLS)
# The service role key allows ALL operations regardless of RLS policies
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)

print(f"✅ Supabase initialized with SERVICE ROLE")
print(f"📡 URL: {SUPABASE_URL}")

# ============================================
# PASSWORD HASHING (without bcrypt)
# ============================================

def hash_password(password):
    """Hash a password using SHA256 with salt"""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password, hashed_password):
    """Verify a password against its hash"""
    try:
        salt, hash_value = hashed_password.split(':')
        check_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        return check_hash == hash_value
    except:
        return False

# ============================================
# HELPER - GENERATE REFERRAL CODE
# ============================================

def generate_referral_code():
    """Generate a unique 8-character referral code"""
    chars = string.ascii_uppercase + string.digits
    # Avoid ambiguous characters (0, O, I, 1)
    chars = chars.replace('0', '').replace('O', '').replace('I', '').replace('1', '')
    code = ''.join(random.choices(chars, k=8))
    return code

def get_unique_referral_code():
    """Generate a unique referral code that doesn't exist in database"""
    attempts = 0
    while attempts < 20:
        code = generate_referral_code()
        # Check if code exists in wallets table
        existing = supabase.table('wallets').select('referral_code').eq('referral_code', code).execute()
        if not existing.data:
            return code
        attempts += 1
    # Fallback to timestamp-based code
    return f"AD{int(time.time()) % 1000000:06d}"

# ============================================
# TOKEN HELPERS
# ============================================

def generate_jwt(user_id, email):
    """Generate JWT token for user"""
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.now(timezone.utc) + timedelta(seconds=JWT_EXPIRATION),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_current_user():
    """Get current user from session or JWT"""
    token = request.headers.get('Authorization')
    if token and token.startswith('Bearer '):
        token = token[7:]
        payload = verify_jwt(token)
        if payload:
            return payload
    return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated

# ============================================
# AUTHENTICATION METHODS
# ============================================

def auth_register(email, password, username=None):
    """Register a new user with auto-generated referral code"""
    try:
        # Check if user already exists in app_users
        existing = supabase.table('app_users').select('*').eq('email', email).execute()
        if existing.data:
            return {'error': 'Email already registered'}, 400
        
        # Hash password
        hashed_password = hash_password(password)
        
        # Create user in auth.users
        auth_user = supabase.auth.sign_up({
            'email': email,
            'password': password
        })
        
        if not auth_user.user:
            return {'error': 'Failed to create user'}, 400
        
        user_id = auth_user.user.id
        
        # Generate unique referral code
        referral_code = get_unique_referral_code()
        
        # Generate wallet
        private_key = secrets.token_bytes(32).hex()
        public_key = hashlib.sha256(private_key.encode()).hexdigest()
        wallet_address = hashlib.sha256(public_key.encode()).hexdigest()[:40]
        
        # Create wallet in wallets table
        wallet_data = {
            'address': wallet_address,
            'private_key': private_key,
            'public_key': public_key,
            'balance': 0,
            'referral_code': referral_code,
            'total_ads_watched': 0,
            'total_ad_rewards': 0,
            'total_mining_sessions': 0,
            'mining_active': False,
            'mining_accumulated': 0,
            'total_mined': 0,
            'total_games_played': 0,
            'total_games_won': 0,
            'total_game_rewards': 0,
            'app_version': '1.0.0',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Check if wallet already exists (shouldn't, but just in case)
        existing_wallet = supabase.table('wallets').select('*').eq('address', wallet_address).execute()
        if not existing_wallet.data:
            supabase.table('wallets').insert(wallet_data).execute()
        else:
            # Update existing wallet
            supabase.table('wallets').update({
                'referral_code': referral_code
            }).eq('address', wallet_address).execute()
        
        # Create user in app_users table
        user_data = {
            'id': user_id,
            'email': email,
            'username': username or email.split('@')[0],
            'wallet_address': wallet_address,
            'wallet_private_key': private_key,
            'wallet_public_key': public_key,
            'referral_code': referral_code,
            'password_hash': hashed_password,
            'balance': 0,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        supabase.table('app_users').insert(user_data).execute()
        
        # Generate JWT
        token = generate_jwt(user_id, email)
        
        return {
            'status': 'success',
            'message': 'User registered successfully',
            'user': {
                'id': user_id,
                'email': email,
                'username': username or email.split('@')[0],
                'wallet_address': wallet_address,
                'referral_code': referral_code,
                'balance': 0
            },
            'token': token
        }, 201
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return {'error': str(e)}, 500

def auth_login(email, password):
    """Login user"""
    try:
        # Find user in app_users
        user = supabase.table('app_users').select('*').eq('email', email).execute()
        if not user.data:
            return {'error': 'Invalid credentials'}, 401
        
        user_data = user.data[0]
        
        # Verify password
        if not verify_password(password, user_data.get('password_hash', '')):
            return {'error': 'Invalid credentials'}, 401
        
        # Update last login
        supabase.table('app_users').update({
            'last_login': datetime.now(timezone.utc).isoformat()
        }).eq('id', user_data['id']).execute()
        
        # Generate JWT
        token = generate_jwt(user_data['id'], email)
        
        # Get wallet info if exists
        wallet = None
        if user_data.get('wallet_address'):
            wallet_result = supabase.table('wallets').select('*').eq('address', user_data['wallet_address']).execute()
            wallet = wallet_result.data[0] if wallet_result.data else None
        
        return {
            'status': 'success',
            'message': 'Login successful',
            'user': {
                'id': user_data['id'],
                'email': user_data['email'],
                'username': user_data.get('username'),
                'wallet_address': user_data.get('wallet_address'),
                'referral_code': user_data.get('referral_code'),
                'balance': user_data.get('balance', 0)
            },
            'token': token,
            'wallet': wallet
        }, 200
    except Exception as e:
        print(f"❌ Login error: {e}")
        return {'error': str(e)}, 500

def auth_logout():
    """Logout user"""
    return {'status': 'success', 'message': 'Logout successful'}, 200

def get_user_profile(user_id):
    """Get user profile from app_users"""
    try:
        result = supabase.table('app_users').select('*').eq('id', user_id).execute()
        if not result.data:
            return {'error': 'User not found'}, 404
        
        user = result.data[0]
        return {
            'id': user['id'],
            'email': user['email'],
            'username': user.get('username'),
            'wallet_address': user.get('wallet_address'),
            'referral_code': user.get('referral_code'),
            'balance': user.get('balance', 0),
            'total_ads_watched': user.get('total_ads_watched', 0),
            'total_ad_rewards': user.get('total_ad_rewards', 0),
            'total_mining_sessions': user.get('total_mining_sessions', 0),
            'total_mined': user.get('total_mined', 0),
            'mining_active': user.get('mining_active', False),
            'created_at': user.get('created_at'),
            'last_login': user.get('last_login')
        }, 200
    except Exception as e:
        return {'error': str(e)}, 500

def bind_wallet_to_user(user_id, wallet_address, private_key, public_key):
    """Bind a wallet to a user"""
    try:
        # Check if wallet already exists
        existing = supabase.table('wallets').select('*').eq('address', wallet_address).execute()
        if not existing.data:
            # Create wallet first
            wallet_data = {
                'address': wallet_address,
                'private_key': private_key,
                'public_key': public_key,
                'balance': 0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            supabase.table('wallets').insert(wallet_data).execute()
        
        # Update user with wallet
        supabase.table('app_users').update({
            'wallet_address': wallet_address,
            'wallet_private_key': private_key,
            'wallet_public_key': public_key,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', user_id).execute()
        
        # Also add to wallet_bindings
        binding_data = {
            'user_id': user_id,
            'wallet_address': wallet_address,
            'wallet_private_key': private_key,
            'wallet_public_key': public_key,
            'is_primary': True
        }
        supabase.table('wallet_bindings').insert(binding_data).execute()
        
        return {'status': 'success', 'message': 'Wallet bound to user'}, 200
    except Exception as e:
        return {'error': str(e)}, 500

def create_wallet_for_user(user_id):
    """Create a new wallet and bind to user"""
    import secrets
    import hashlib
    
    try:
        private_key = secrets.token_bytes(32).hex()
        public_key = hashlib.sha256(private_key.encode()).hexdigest()
        address = hashlib.sha256(public_key.encode()).hexdigest()[:40]
        
        return bind_wallet_to_user(user_id, address, private_key, public_key)
    except Exception as e:
        return {'error': str(e)}, 500

def get_user_wallet(user_id):
    """Get user's wallet"""
    try:
        result = supabase.table('app_users').select('wallet_address, balance').eq('id', user_id).execute()
        if not result.data:
            return {'error': 'User not found'}, 404
        
        user = result.data[0]
        if not user.get('wallet_address'):
            return {'error': 'No wallet bound to user'}, 404
        
        wallet = supabase.table('wallets').select('*').eq('address', user['wallet_address']).execute()
        return wallet.data[0] if wallet.data else {'error': 'Wallet not found'}, 404
    except Exception as e:
        return {'error': str(e)}, 500

def verify_session(token):
    """Verify user session"""
    payload = verify_jwt(token)
    if not payload:
        return None
    
    # Check if user exists in app_users
    result = supabase.table('app_users').select('*').eq('id', payload['user_id']).execute()
    if not result.data:
        return None
    
    return payload

def auth_check():
    """Check if user is authenticated"""
    user = get_current_user()
    if user:
        return {'authenticated': True, 'user': user}, 200
    return {'authenticated': False}, 401
