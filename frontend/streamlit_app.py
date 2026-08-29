import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import os
import json

# ============================================
# CONFIGURATION
# ============================================
API_URL = os.getenv('API_URL', 'https://admine-kgvk.onrender.com')
TOKEN_SYMBOL = "ADT"
APP_NAME = "AdMine Admin"

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title=f"{APP_NAME} - {TOKEN_SYMBOL} Admin",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CUSTOM CSS
# ============================================
st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #2d2d44 100%);
        padding: 20px 30px;
        border-radius: 15px;
        margin-bottom: 25px;
        border: 1px solid #2d2d44;
    }
    .admin-badge {
        background: #f5576c;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        letter-spacing: 1px;
        display: inline-block;
    }
    .stat-card {
        background: #1a1a2e;
        padding: 18px 20px;
        border-radius: 12px;
        border: 1px solid #2d2d44;
        margin-bottom: 10px;
    }
    .stat-number {
        font-size: 28px;
        font-weight: bold;
        color: #ffffff;
    }
    .stat-label {
        font-size: 13px;
        color: #8899aa;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .admin-action {
        background: #1a1a2e;
        padding: 15px 20px;
        border-radius: 12px;
        border-left: 4px solid #667eea;
        margin-bottom: 10px;
    }
    .admin-action-success {
        border-left-color: #00d2ff;
    }
    .admin-action-warning {
        border-left-color: #f093fb;
    }
    .admin-action-danger {
        border-left-color: #f5576c;
    }
    .config-input {
        background: #0f0f1a;
        padding: 10px;
        border-radius: 8px;
        margin: 5px 0;
    }
    .footer {
        text-align: center;
        padding: 20px;
        color: #556677;
        font-size: 12px;
        border-top: 1px solid #2d2d44;
        margin-top: 40px;
    }
    .supply-display {
        font-size: 24px;
        font-weight: bold;
        color: #00d2ff;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================
# AUTHENTICATION
# ============================================
ADMIN_CREDENTIALS = {
    "admin": "admin123",
    "merlito": "merlito456"
}

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'config_changed' not in st.session_state:
    st.session_state.config_changed = False

def check_auth():
    """Check if user is authenticated"""
    if not st.session_state.authenticated:
        st.markdown("""
        <div style="max-width: 400px; margin: 100px auto; padding: 40px; background: #1a1a2e; border-radius: 15px; border: 1px solid #2d2d44;">
            <h2 style="color: #667eea; text-align: center;">⚙️ Admin Access</h2>
            <p style="color: #8899aa; text-align: center; margin-bottom: 30px;">Enter credentials to access the admin dashboard</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            username = st.text_input("👤 Username", placeholder="admin")
            password = st.text_input("🔑 Password", type="password", placeholder="••••••••")
            
            if st.button("🔓 Login", use_container_width=True, type="primary"):
                if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == password:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success("✅ Login successful!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials!")
        
        st.stop()

check_auth()

# ============================================
# API HELPER FUNCTIONS
# ============================================
@st.cache_data(ttl=5)
def api_request(endpoint, method='GET', data=None):
    """Make API request with caching"""
    try:
        url = f"{API_URL}{endpoint}"
        if method == 'GET':
            r = requests.get(url, timeout=10)
        else:
            r = requests.post(url, json=data, timeout=10)
        
        if r.status_code == 200:
            return r.json(), None
        return None, f"HTTP {r.status_code}"
    except requests.exceptions.ConnectionError:
        return None, "Backend offline"
    except Exception as e:
        return None, str(e)

def refresh_data():
    """Force refresh cached data"""
    st.cache_data.clear()
    st.rerun()

# ============================================
# HEADER
# ============================================
st.markdown(f"""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="color: white; margin: 0; font-size: 32px;">⚙️ {APP_NAME}</h1>
            <div style="display: flex; gap: 10px; margin-top: 5px;">
                <span class="admin-badge">ADMIN</span>
                <span style="color: #8899aa; font-size: 13px;">{TOKEN_SYMBOL} Blockchain Monitor</span>
            </div>
        </div>
        <div style="text-align: right;">
            <div style="color: #8899aa; font-size: 12px;">
                {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
            <div style="color: #00d2ff; font-size: 12px; margin-top: 4px;">
                🔗 {API_URL}
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================
# SYSTEM STATUS
# ============================================
backend_data, backend_error = api_request('/api/token-info')
chain_data, chain_error = api_request('/api/blockchain')

# Status bar
col_status1, col_status2, col_status3, col_status4, col_status5 = st.columns(5)

with col_status1:
    if backend_data:
        st.success("✅ Backend: Online")
    else:
        st.error("❌ Backend: Offline")

with col_status2:
    if chain_data:
        blocks = len(chain_data.get('chain', []))
        st.info(f"⛓️ Blocks: {blocks}")
    else:
        st.warning("⚠️ No chain data")

with col_status3:
    if backend_data:
        supply = backend_data.get('total_supply', 0)
        st.info(f"🪙 Supply: {supply:,} {TOKEN_SYMBOL}")
    else:
        st.warning("⚠️ Unknown")

with col_status4:
    if backend_data:
        reward = backend_data.get('mining_reward', 10)
        st.info(f"⛏️ Reward: {reward} {TOKEN_SYMBOL}")
    else:
        st.warning("⚠️ Unknown")

with col_status5:
    if st.button("🔄 Refresh", use_container_width=True):
        refresh_data()

st.markdown("---")

# ============================================
# ADMIN DASHBOARD - TABS
# ============================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard",
    "⛏️ Mining Controls",
    "🪙 Token Supply",
    "⚙️ Configurations",
    "📝 Transactions"
])

# ============================================
# TAB 1: DASHBOARD
# ============================================
with tab1:
    col1, col2, col3 = st.columns([1, 1.2, 0.8])
    
    with col1:
        st.subheader("📊 System Statistics")
        
        stats_data, _ = api_request('/api/stats')
        
        if stats_data:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">📦 Total Blocks</div>
                <div class="stat-number">{stats_data.get('total_blocks', 0)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">📝 Total Transactions</div>
                <div class="stat-number">{stats_data.get('total_transactions', 0)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">👛 Total Wallets</div>
                <div class="stat-number">{stats_data.get('total_wallets', 0)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">🪙 Total Supply</div>
                <div class="stat-number">{stats_data.get('total_supply', 0):.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Stats unavailable")
        
        st.markdown("---")
        
        # Top Wallets
        st.subheader("🏆 Top Wallets")
        wallets_data, _ = api_request('/api/wallets/top?limit=10')
        if wallets_data:
            wallets = wallets_data.get('wallets', [])
            if wallets:
                for i, wallet in enumerate(wallets[:5], 1):
                    addr = wallet.get('address', 'unknown')[:15] + "..."
                    balance = wallet.get('balance', 0)
                    medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1] if i <= 5 else "•"
                    st.markdown(f"""
                    <div style="background: #1a1a2e; padding: 8px 12px; border-radius: 8px; margin-bottom: 5px; border: 1px solid #2d2d44;">
                        <span style="font-size: 14px;">
                            {medal} {addr} 
                            <span style="float: right; color: #00d2ff;">{balance:.2f} {TOKEN_SYMBOL}</span>
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("No wallets found")
        else:
            st.caption("No data")
    
    with col2:
        st.subheader("🔗 Blockchain Explorer")
        
        if chain_data:
            chain = chain_data.get('chain', [])
            
            st.metric("📏 Block Height", len(chain))
            st.metric("🎯 Difficulty", chain_data.get('difficulty', 4))
            st.metric("⛏️ Mining Reward", f"{chain_data.get('mining_reward', 10)} {TOKEN_SYMBOL}")
            
            st.markdown("### 📦 Latest Blocks")
            if chain:
                latest_blocks = chain[-10:][::-1]
                blocks_data = []
                for block in latest_blocks:
                    blocks_data.append({
                        "Block": block.get('index', 0),
                        "Hash": block.get('hash', 'N/A')[:12] + "...",
                        "Txs": len(block.get('transactions', [])),
                        "Nonce": block.get('nonce', 0)
                    })
                df = pd.DataFrame(blocks_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.markdown("### 📝 Pending Transactions")
            pending = chain_data.get('pending_transactions', [])
            st.metric("Pending", len(pending))
            if pending:
                for tx in pending[:3]:
                    st.caption(f"{tx.get('from', '')[:10]} → {tx.get('to', '')[:10]}: {tx.get('amount', 0)} {TOKEN_SYMBOL}")
        else:
            st.warning("⚠️ Blockchain data unavailable")
    
    with col3:
        st.subheader("🪙 Token Information")
        if backend_data:
            st.markdown(f"""
            <div style="background: #1a1a2e; padding: 15px; border-radius: 12px; border: 1px solid #2d2d44;">
                <div style="display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #2d2d44;">
                    <span style="color: #8899aa;">Name</span>
                    <span style="color: white;">{backend_data.get('name', 'AdToken')}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #2d2d44;">
                    <span style="color: #8899aa;">Symbol</span>
                    <span style="color: #00d2ff; font-weight: bold;">{backend_data.get('symbol', TOKEN_SYMBOL)}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #2d2d44;">
                    <span style="color: #8899aa;">Decimals</span>
                    <span style="color: white;">{backend_data.get('decimals', 18)}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 5px 0;">
                    <span style="color: #8899aa;">Total Supply</span>
                    <span style="color: #f093fb;">{backend_data.get('total_supply', 0):,}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("🩺 System Health")
        
        health_checks = {
            "Backend API": backend_data is not None,
            "Blockchain": chain_data is not None,
            "Supabase": backend_data is not None
        }
        for component, status in health_checks.items():
            if status:
                st.success(f"✅ {component}")
            else:
                st.error(f"❌ {component}")

# ============================================
# TAB 2: MINING CONTROLS
# ============================================
with tab2:
    st.subheader("⛏️ Mining Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="admin-action admin-action-success">
            <strong>⛏️ Force Mine</strong>
            <p style="color: #8899aa; font-size: 12px;">Manually mine all pending transactions</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("⛏️ Force Mine Now", use_container_width=True, type="primary"):
            with st.spinner("⛏️ Mining..."):
                data, error = api_request('/api/mine', 'POST', {"address": "admin_wallet"})
                if data and not error:
                    st.success(f"✅ {data.get('message', 'Block mined!')}")
                    refresh_data()
                else:
                    st.error(f"❌ {error}")
        
        st.markdown("---")
        
        st.markdown("""
        <div class="admin-action admin-action-warning">
            <strong>🎯 Set Mining Difficulty</strong>
            <p style="color: #8899aa; font-size: 12px;">Higher difficulty = harder to mine</p>
        </div>
        """, unsafe_allow_html=True)
        
        current_diff = chain_data.get('difficulty', 4) if chain_data else 4
        new_diff = st.number_input("Difficulty Level", min_value=1, max_value=10, value=current_diff)
        
        if st.button("Update Difficulty", use_container_width=True):
            with st.spinner("Updating..."):
                data, error = api_request('/api/config/difficulty', 'POST', {"difficulty": new_diff})
                if data and not error:
                    st.success(f"✅ Difficulty updated to {new_diff}")
                    refresh_data()
                else:
                    st.error(f"❌ {error}")
    
    with col2:
        st.markdown("""
        <div class="admin-action admin-action-success">
            <strong>💎 Set Block Reward</strong>
            <p style="color: #8899aa; font-size: 12px;">Amount of {TOKEN_SYMBOL} rewarded per block</p>
        </div>
        """.replace('{TOKEN_SYMBOL}', TOKEN_SYMBOL), unsafe_allow_html=True)
        
        current_reward = chain_data.get('mining_reward', 10) if chain_data else 10
        new_reward = st.number_input(f"Block Reward ({TOKEN_SYMBOL})", min_value=0.1, max_value=100.0, value=float(current_reward), step=0.5)
        
        if st.button("Update Block Reward", use_container_width=True):
            with st.spinner("Updating..."):
                data, error = api_request('/api/config/reward', 'POST', {"reward": new_reward})
                if data and not error:
                    st.success(f"✅ Block reward updated to {new_reward} {TOKEN_SYMBOL}")
                    refresh_data()
                else:
                    st.error(f"❌ {error}")
        
        st.markdown("---")
        
        st.markdown("""
        <div class="admin-action admin-action-warning">
            <strong>📺 Set Ad Reward</strong>
            <p style="color: #8899aa; font-size: 12px;">Amount of {TOKEN_SYMBOL} per ad view</p>
        </div>
        """.replace('{TOKEN_SYMBOL}', TOKEN_SYMBOL), unsafe_allow_html=True)
        
        current_ad = chain_data.get('ad_reward', 0.5) if chain_data else 0.5
        new_ad = st.number_input(f"Ad Reward ({TOKEN_SYMBOL})", min_value=0.01, max_value=10.0, value=float(current_ad), step=0.1)
        
        if st.button("Update Ad Reward", use_container_width=True):
            with st.spinner("Updating..."):
                data, error = api_request('/api/config/ad-reward', 'POST', {"ad_reward": new_ad})
                if data and not error:
                    st.success(f"✅ Ad reward updated to {new_ad} {TOKEN_SYMBOL}")
                    refresh_data()
                else:
                    st.error(f"❌ {error}")

# ============================================
# TAB 3: TOKEN SUPPLY
# ============================================
with tab3:
    st.subheader("🪙 Token Supply Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="admin-action admin-action-success">
            <strong>💰 Mint New Tokens</strong>
            <p style="color: #8899aa; font-size: 12px;">Create additional {TOKEN_SYMBOL} tokens</p>
        </div>
        """.replace('{TOKEN_SYMBOL}', TOKEN_SYMBOL), unsafe_allow_html=True)
        
        mint_amount = st.number_input(f"Amount to Mint ({TOKEN_SYMBOL})", min_value=0.01, max_value=1000000.0, value=100.0, step=10.0)
        mint_address = st.text_input("Destination Wallet Address", placeholder="0x...")
        
        if st.button("🪙 Mint Tokens", use_container_width=True, type="primary"):
            if not mint_address:
                st.error("❌ Please enter a wallet address")
            else:
                with st.spinner("Minting..."):
                    data, error = api_request('/api/admin/mint', 'POST', {
                        "address": mint_address,
                        "amount": mint_amount
                    })
                    if data and not error:
                        st.success(f"✅ Minted {mint_amount} {TOKEN_SYMBOL} to {mint_address[:15]}...")
                        refresh_data()
                    else:
                        st.error(f"❌ {error}")
        
        st.markdown("---")
        
        st.markdown("""
        <div class="admin-action admin-action-warning">
            <strong>🔥 Burn Tokens</strong>
            <p style="color: #8899aa; font-size: 12px;">Remove {TOKEN_SYMBOL} from circulation</p>
        </div>
        """.replace('{TOKEN_SYMBOL}', TOKEN_SYMBOL), unsafe_allow_html=True)
        
        burn_amount = st.number_input(f"Amount to Burn ({TOKEN_SYMBOL})", min_value=0.01, max_value=1000000.0, value=50.0, step=10.0)
        burn_address = st.text_input("Wallet Address to Burn From", placeholder="0x...")
        
        if st.button("🔥 Burn Tokens", use_container_width=True):
            if not burn_address:
                st.error("❌ Please enter a wallet address")
            else:
                with st.spinner("Burning..."):
                    data, error = api_request('/api/admin/burn', 'POST', {
                        "address": burn_address,
                        "amount": burn_amount
                    })
                    if data and not error:
                        st.success(f"✅ Burned {burn_amount} {TOKEN_SYMBOL} from {burn_address[:15]}...")
                        refresh_data()
                    else:
                        st.error(f"❌ {error}")
    
    with col2:
        st.markdown("""
        <div class="admin-action admin-action-success">
            <strong>📊 Supply Statistics</strong>
        </div>
        """, unsafe_allow_html=True)
        
        if stats_data:
            st.metric("Total Supply", f"{stats_data.get('total_supply', 0):.2f} {TOKEN_SYMBOL}")
            st.metric("Total Wallets", stats_data.get('total_wallets', 0))
            st.metric("Total Transactions", stats_data.get('total_transactions', 0))
            st.metric("Max Supply", f"{backend_data.get('total_supply', 100000000):,} {TOKEN_SYMBOL}" if backend_data else "Unknown")
        
        st.markdown("---")
        
        st.markdown("""
        <div class="admin-action admin-action-danger">
            <strong>⚠️ Reset Blockchain</strong>
            <p style="color: #8899aa; font-size: 12px;">⚠️ WARNING: This will delete all data!</p>
        </div>
        """, unsafe_allow_html=True)
        
        confirm = st.checkbox("I understand this action is irreversible")
        if st.button("🗑️ Reset Blockchain", use_container_width=True, disabled=not confirm):
            if confirm:
                with st.spinner("Resetting..."):
                    data, error = api_request('/api/admin/reset', 'POST')
                    if data and not error:
                        st.success("✅ Blockchain reset successfully")
                        refresh_data()
                    else:
                        st.error(f"❌ {error}")

# ============================================
# TAB 4: CONFIGURATIONS
# ============================================
with tab4:
    st.subheader("⚙️ Advanced Configurations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="admin-action admin-action-success">
            <strong>📝 Update Token Name</strong>
        </div>
        """, unsafe_allow_html=True)
        
        current_name = backend_data.get('name', 'AdToken') if backend_data else 'AdToken'
        new_name = st.text_input("Token Name", value=current_name)
        
        if st.button("Update Token Name", use_container_width=True):
            with st.spinner("Updating..."):
                data, error = api_request('/api/config/token-name', 'POST', {"name": new_name})
                if data and not error:
                    st.success(f"✅ Token name updated to {new_name}")
                    refresh_data()
                else:
                    st.error(f"❌ {error}")
        
        st.markdown("""
        <div class="admin-action admin-action-warning">
            <strong>📝 Update Token Symbol</strong>
        </div>
        """, unsafe_allow_html=True)
        
        current_symbol = backend_data.get('symbol', TOKEN_SYMBOL) if backend_data else TOKEN_SYMBOL
        new_symbol = st.text_input("Token Symbol", value=current_symbol, max_chars=5)
        
        if st.button("Update Token Symbol", use_container_width=True):
            with st.spinner("Updating..."):
                data, error = api_request('/api/config/token-symbol', 'POST', {"symbol": new_symbol})
                if data and not error:
                    st.success(f"✅ Token symbol updated to {new_symbol}")
                    refresh_data()
                else:
                    st.error(f"❌ {error}")
    
    with col2:
        st.markdown("""
        <div class="admin-action admin-action-success">
            <strong>🔑 Set Admin Wallet</strong>
        </div>
        """, unsafe_allow_html=True)
        
        admin_wallet = st.text_input("Admin Wallet Address", placeholder="0x...")
        
        if st.button("Set Admin Wallet", use_container_width=True):
            with st.spinner("Updating..."):
                data, error = api_request('/api/config/admin-wallet', 'POST', {"address": admin_wallet})
                if data and not error:
                    st.success("✅ Admin wallet updated")
                    refresh_data()
                else:
                    st.error(f"❌ {error}")
        
        st.markdown("""
        <div class="admin-action admin-action-warning">
            <strong>📊 Export Blockchain Data</strong>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📥 Export Blockchain", use_container_width=True):
            with st.spinner("Exporting..."):
                data, error = api_request('/api/admin/export')
                if data and not error:
                    st.download_button(
                        label="📥 Download JSON",
                        data=json.dumps(data, indent=2),
                        file_name=f"blockchain_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                else:
                    st.error(f"❌ {error}")

# ============================================
# TAB 5: TRANSACTIONS
# ============================================
with tab5:
    st.subheader("📝 Transaction Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="admin-action admin-action-success">
            <strong>💸 Send Tokens</strong>
            <p style="color: #8899aa; font-size: 12px;">Send {TOKEN_SYMBOL} from admin wallet</p>
        </div>
        """.replace('{TOKEN_SYMBOL}', TOKEN_SYMBOL), unsafe_allow_html=True)
        
        send_to = st.text_input("Recipient Address", placeholder="0x...")
        send_amount = st.number_input(f"Amount ({TOKEN_SYMBOL})", min_value=0.01, max_value=1000000.0, value=10.0)
        send_note = st.text_input("Note (optional)")
        
        if st.button("💸 Send Tokens", use_container_width=True, type="primary"):
            if not send_to:
                st.error("❌ Please enter a recipient address")
            else:
                with st.spinner("Sending..."):
                    data, error = api_request('/api/admin/send', 'POST', {
                        "to": send_to,
                        "amount": send_amount,
                        "note": send_note
                    })
                    if data and not error:
                        st.success(f"✅ Sent {send_amount} {TOKEN_SYMBOL} to {send_to[:15]}...")
                        refresh_data()
                    else:
                        st.error(f"❌ {error}")
    
    with col2:
        st.markdown("""
        <div class="admin-action admin-action-warning">
            <strong>🔍 Transaction Search</strong>
        </div>
        """, unsafe_allow_html=True)
        
        search_address = st.text_input("Search by Wallet Address", placeholder="0x...")
        
        if search_address and st.button("🔍 Search", use_container_width=True):
            with st.spinner("Searching..."):
                data, error = api_request(f'/api/wallet/{search_address}/transactions')
                if data and not error:
                    txs = data.get('transactions', [])
                    if txs:
                        st.success(f"✅ Found {len(txs)} transactions")
                        df = pd.DataFrame(txs)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No transactions found")
                else:
                    st.error(f"❌ {error}")

# ============================================
# FOOTER
# ============================================
st.markdown(f"""
<div class="footer">
    <p>⚙️ <b>AdMine Admin</b> · {TOKEN_SYMBOL} Blockchain Monitor</p>
    <p style="font-size: 11px; color: #445566;">
        API: {API_URL} · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </p>
</div>
""", unsafe_allow_html=True)
