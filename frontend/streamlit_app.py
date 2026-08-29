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
API_URL = os.getenv('API_URL', 'http://localhost:5000')
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
    /* Main header */
    .main-header {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #2d2d44 100%);
        padding: 20px 30px;
        border-radius: 15px;
        margin-bottom: 25px;
        border: 1px solid #2d2d44;
    }
    
    /* Admin badge */
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
    
    /* Status cards */
    .stat-card {
        background: #1a1a2e;
        padding: 18px 20px;
        border-radius: 12px;
        border: 1px solid #2d2d44;
        margin-bottom: 10px;
    }
    
    .stat-card:hover {
        border-color: #667eea;
        transition: 0.3s;
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
    
    /* Tables */
    .data-table {
        background: #1a1a2e;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #2d2d44;
    }
    
    /* Admin actions */
    .admin-action {
        background: #1a1a2e;
        padding: 15px;
        border-radius: 12px;
        border-left: 4px solid #667eea;
        margin-bottom: 10px;
    }
    
    /* Status indicators */
    .status-online {
        color: #00d2ff;
        font-weight: bold;
    }
    
    .status-offline {
        color: #f5576c;
        font-weight: bold;
    }
    
    .status-warning {
        color: #f093fb;
        font-weight: bold;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 20px;
        color: #556677;
        font-size: 12px;
        border-top: 1px solid #2d2d44;
        margin-top: 40px;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================
# AUTHENTICATION (Hardcoded Admin)
# ============================================
ADMIN_CREDENTIALS = {
    "admin": "admin123",
    "merlito": "merlito456"
}

def check_auth():
    """Check if user is authenticated"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
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
            r = requests.get(url, timeout=5)
        else:
            r = requests.post(url, json=data, timeout=5)
        
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
            <button onclick="location.reload()" style="background: #2d2d44; border: none; color: #8899aa; padding: 5px 15px; border-radius: 5px; cursor: pointer; margin-top: 5px;">
                🔄 Refresh
            </button>
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
col_status1, col_status2, col_status3, col_status4 = st.columns(4)

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
    if st.button("🔄 Refresh All", use_container_width=True):
        refresh_data()

st.markdown("---")

# ============================================
# ADMIN DASHBOARD - 3 COLUMNS
# ============================================
col1, col2, col3 = st.columns([1, 1.2, 0.8])

# ============================================
# COLUMN 1 - SYSTEM STATS
# ============================================
with col1:
    st.subheader("📊 System Statistics")
    
    # Get stats
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
    
    # ============================================
    # TOP WALLETS
    # ============================================
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

# ============================================
# COLUMN 2 - BLOCKCHAIN EXPLORER
# ============================================
with col2:
    st.subheader("🔗 Blockchain Explorer")
    
    if chain_data:
        chain = chain_data.get('chain', [])
        
        # Block height
        st.metric("📏 Block Height", len(chain))
        
        # Difficulty
        st.metric("🎯 Difficulty", chain_data.get('difficulty', 4))
        
        # Mining reward
        st.metric("⛏️ Mining Reward", f"{chain_data.get('mining_reward', 10)} {TOKEN_SYMBOL}")
        
        # ============================================
        # LATEST BLOCKS TABLE
        # ============================================
        st.markdown("### 📦 Latest Blocks")
        
        if chain:
            # Show last 10 blocks
            latest_blocks = chain[-10:][::-1]  # Reverse to show newest first
            
            blocks_data = []
            for block in latest_blocks:
                blocks_data.append({
                    "Block": block.get('index', 0),
                    "Hash": block.get('hash', 'N/A')[:12] + "...",
                    "Txs": len(block.get('transactions', [])),
                    "Nonce": block.get('nonce', 0),
                    "Time": datetime.fromtimestamp(block.get('timestamp', 0)).strftime('%H:%M:%S') if block.get('timestamp') else "N/A"
                })
            
            df = pd.DataFrame(blocks_data)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Block": "Block",
                    "Hash": "Hash",
                    "Txs": "Txs",
                    "Nonce": "Nonce",
                    "Time": "Time"
                }
            )
        else:
            st.info("No blocks yet")
        
        # ============================================
        # PENDING TRANSACTIONS
        # ============================================
        st.markdown("### 📝 Pending Transactions")
        pending = chain_data.get('pending_transactions', [])
        st.metric("Pending", len(pending))
        
        if pending:
            for tx in pending[:5]:
                st.markdown(f"""
                <div style="background: #1a1a2e; padding: 6px 10px; border-radius: 6px; margin-bottom: 4px; font-size: 13px; border-left: 3px solid #f093fb;">
                    {tx.get('from', '')[:10]} → {tx.get('to', '')[:10]}
                    <span style="float: right; color: #00d2ff;">{tx.get('amount', 0)} {TOKEN_SYMBOL}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No pending transactions")
    
    else:
        st.warning("⚠️ Blockchain data unavailable")

# ============================================
# COLUMN 3 - ADMIN ACTIONS & TOKEN INFO
# ============================================
with col3:
    st.subheader("⚙️ Admin Actions")
    
    # ============================================
    # ADMIN ACTIONS
    # ============================================
    st.markdown("""
    <div class="admin-action">
        <strong>⛏️ Force Mine</strong>
        <p style="color: #8899aa; font-size: 12px;">Manually mine pending transactions</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("⛏️ Force Mine Now", use_container_width=True):
        with st.spinner("Mining..."):
            data, error = api_request('/api/mine', 'POST', {"address": "admin_wallet"})
            if data and not error:
                st.success("✅ Mining initiated!")
                time.sleep(1)
                refresh_data()
            else:
                st.error(f"❌ {error}")
    
    st.markdown("---")
    
    # ============================================
    # TOKEN INFO
    # ============================================
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
    
    # ============================================
    # SYSTEM HEALTH
    # ============================================
    st.subheader("🩺 System Health")
    
    # Check components
    health_checks = {
        "Backend API": backend_data is not None,
        "Blockchain": chain_data is not None,
        "Database": True  # Could add DB check
    }
    
    for component, status in health_checks.items():
        if status:
            st.success(f"✅ {component}: OK")
        else:
            st.error(f"❌ {component}: Failed")
    
    st.markdown("---")
    
    # ============================================
    # USER SESSION
    # ============================================
    st.subheader("👤 Admin Session")
    st.caption(f"Logged in as: **{username}**")
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

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

# ============================================
# AUTO-REFRESH (Every 15 seconds)
# ============================================
if st.button("🔄 Auto-Refresh (15s)", use_container_width=True):
    st.cache_data.clear()
    time.sleep(15)
    st.rerun()
