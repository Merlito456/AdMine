import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
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
    .mining-active {
        background: #00d2ff22;
        border: 1px solid #00d2ff;
        padding: 10px 15px;
        border-radius: 10px;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    .mining-inactive {
        background: #1a1a2e;
        padding: 10px 15px;
        border-radius: 10px;
        border: 1px solid #2d2d44;
    }
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
# AUTHENTICATION
# ============================================
ADMIN_CREDENTIALS = {
    "admin": "admin123",
    "merlito": "merlito456"
}

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'mining_address' not in st.session_state:
    st.session_state.mining_address = None

def check_auth():
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
mining_rate, _ = api_request('/api/mining/rate')

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
    if mining_rate:
        rate = mining_rate.get('hourly_rate', 0.5)
        st.info(f"⛏️ Rate: {rate} {TOKEN_SYMBOL}/hr")
    else:
        st.warning("⚠️ Unknown")

with col_status5:
    if st.button("🔄 Refresh", use_container_width=True):
        refresh_data()

st.markdown("---")

# ============================================
# ADMIN DASHBOARD - TABS
# ============================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Dashboard",
    "⛏️ Mining",
    "🪙 Token Supply",
    "⚙️ Configurations",
    "📝 Transactions",
    "👛 Wallets"
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
                <div class="stat-number">{stats_data.get('total_supply', 0):.4f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">⏱️ Mining Rate</div>
                <div class="stat-number">{stats_data.get('hourly_mining_rate', 0.5)} {TOKEN_SYMBOL}/hr</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Stats unavailable")
        
        st.markdown("---")
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
                            <span style="float: right; color: #00d2ff;">{balance:.4f} {TOKEN_SYMBOL}</span>
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
            
            if mining_rate:
                st.metric("⛏️ Hourly Rate", f"{mining_rate.get('hourly_rate', 0.5)} {TOKEN_SYMBOL}/hr")
                st.metric("📊 Daily Cap", f"{mining_rate.get('daily_cap', 12)} {TOKEN_SYMBOL}/day")
            
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
                <div style="display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #2d2d44;">
                    <span style="color: #8899aa;">Total Supply</span>
                    <span style="color: #f093fb;">{backend_data.get('total_supply', 0):,}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 5px 0;">
                    <span style="color: #8899aa;">Max Supply</span>
                    <span style="color: #f5576c;">{backend_data.get('max_supply', 100000000):,}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("🩺 System Health")
        
        health_checks = {
            "Backend API": backend_data is not None,
            "Blockchain": chain_data is not None,
            "Supabase": backend_data is not None,
            "Mining System": mining_rate is not None
        }
        for component, status in health_checks.items():
            if status:
                st.success(f"✅ {component}")
            else:
                st.error(f"❌ {component}")

# ============================================
# TAB 2: MINING
# ============================================
with tab2:
    st.subheader("⛏️ Mining Management")
    
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.markdown("""
        <div class="admin-action admin-action-success">
            <strong>⛏️ Time-Based Mining</strong>
            <p style="color: #8899aa; font-size: 12px;">Earn {TOKEN_SYMBOL} by mining continuously</p>
        </div>
        """.replace('{TOKEN_SYMBOL}', TOKEN_SYMBOL), unsafe_allow_html=True)
        
        # Mining rate display
        if mining_rate:
            st.info(f"""
            **Current Mining Rate:** {mining_rate.get('hourly_rate', 0.5)} {TOKEN_SYMBOL}/hour  
            **Daily Cap:** {mining_rate.get('daily_cap', 12)} {TOKEN_SYMBOL}/day  
            **Claim Interval:** {mining_rate.get('claim_interval_hours', 24)} hours
            """)
        
        # Wallet address input
        mining_address = st.text_input("Wallet Address for Mining", placeholder="Enter wallet address...")
        
        if not mining_address and st.session_state.mining_address:
            mining_address = st.session_state.mining_address
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            if st.button("▶️ Start Mining", use_container_width=True, type="primary"):
                if not mining_address:
                    st.error("❌ Please enter a wallet address")
                else:
                    with st.spinner("Starting mining..."):
                        data, error = api_request('/api/mining/start', 'POST', {"address": mining_address})
                        if data and not error:
                            st.session_state.mining_address = mining_address
                            st.success(f"✅ {data.get('message', 'Mining started!')}")
                            refresh_data()
                        else:
                            st.error(f"❌ {error}")
        
        with col_btn2:
            if st.button("⏹️ Stop Mining", use_container_width=True):
                if not mining_address:
                    st.error("❌ Please enter a wallet address")
                else:
                    with st.spinner("Stopping mining..."):
                        data, error = api_request('/api/mining/stop', 'POST', {"address": mining_address})
                        if data and not error:
                            st.success(f"✅ {data.get('message', 'Mining stopped!')}")
                            if data.get('reward'):
                                st.balloons()
                                st.info(f"💰 Earned: {data.get('reward'):.6f} {TOKEN_SYMBOL}")
                            refresh_data()
                        else:
                            st.error(f"❌ {error}")
        
        with col_btn3:
            if st.button("🔄 Check Status", use_container_width=True):
                if not mining_address:
                    st.error("❌ Please enter a wallet address")
                else:
                    with st.spinner("Checking..."):
                        data, error = api_request(f'/api/mining/status/{mining_address}')
                        if data and not error:
                            st.session_state.mining_address = mining_address
                            if data.get('status') == 'active':
                                st.success("🟢 Mining is ACTIVE")
                                st.info(f"""
                                **Duration:** {data.get('duration', '0.00 hours')}  
                                **Reward So Far:** {data.get('reward_so_far', '0')}  
                                **Hourly Rate:** {data.get('hourly_rate', 'N/A')}  
                                **Daily Cap:** {data.get('daily_cap', 'N/A')}
                                """)
                            else:
                                st.warning("🔴 Mining is INACTIVE")
                                st.info(f"Hourly Rate: {data.get('rate', 0.5)} {TOKEN_SYMBOL}/hour")
                        else:
                            st.error(f"❌ {error}")
        
        st.markdown("---")
        
        # Mining Stats
        if mining_address:
            st.subheader("📊 Mining Statistics")
            stats_data, _ = api_request(f'/api/mining/stats/{mining_address}')
            if stats_data and not stats_data.get('error'):
                st.markdown(f"""
                <div style="background: #1a1a2e; padding: 15px; border-radius: 12px; border: 1px solid #2d2d44;">
                    <div style="display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #2d2d44;">
                        <span style="color: #8899aa;">Total Mined</span>
                        <span style="color: #00d2ff;">{stats_data.get('total_mined', 0):.6f} {TOKEN_SYMBOL}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #2d2d44;">
                        <span style="color: #8899aa;">Current Balance</span>
                        <span style="color: #f093fb;">{stats_data.get('balance', 0):.6f} {TOKEN_SYMBOL}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 5px 0;">
                        <span style="color: #8899aa;">Status</span>
                        <span style="color: {'#00d2ff' if stats_data.get('mining_active') else '#f5576c'};">
                            {'🟢 Active' if stats_data.get('mining_active') else '🔴 Inactive'}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.caption("No mining data available for this address")
    
    with col2:
        st.subheader("⚙️ Mining Configuration (Admin)")
        
        st.markdown("""
        <div class="admin-action admin-action-warning">
            <strong>📊 Update Mining Rate</strong>
            <p style="color: #8899aa; font-size: 12px;">Set hourly mining rate in {TOKEN_SYMBOL}</p>
        </div>
        """.replace('{TOKEN_SYMBOL}', TOKEN_SYMBOL), unsafe_allow_html=True)
        
        current_rate = mining_rate.get('hourly_rate', 0.5) if mining_rate else 0.5
        new_rate = st.number_input("Hourly Rate (ADT/hour)", min_value=0.01, max_value=100.0, value=float(current_rate), step=0.1)
        
        if st.button("Update Mining Rate", use_container_width=True):
            with st.spinner("Updating..."):
                data, error = api_request('/api/mining/config', 'POST', {"hourly_rate": new_rate})
                if data and not error:
                    st.success(f"✅ Mining rate updated to {new_rate} {TOKEN_SYMBOL}/hour")
                    refresh_data()
                else:
                    st.error(f"❌ {error}")
        
        st.markdown("---")
        
        st.markdown("""
        <div class="admin-action admin-action-warning">
            <strong>📊 Update Daily Cap</strong>
            <p style="color: #8899aa; font-size: 12px;">Maximum {TOKEN_SYMBOL} per day</p>
        </div>
        """.replace('{TOKEN_SYMBOL}', TOKEN_SYMBOL), unsafe_allow_html=True)
        
        current_cap = mining_rate.get('daily_cap', 12) if mining_rate else 12
        new_cap = st.number_input("Daily Cap (ADT)", min_value=0.1, max_value=1000.0, value=float(current_cap), step=0.5)
        
        if st.button("Update Daily Cap", use_container_width=True):
            with st.spinner("Updating..."):
                data, error = api_request('/api/mining/config', 'POST', {"daily_cap": new_cap})
                if data and not error:
                    st.success(f"✅ Daily cap updated to {new_cap} {TOKEN_SYMBOL}/day")
                    refresh_data()
                else:
                    st.error(f"❌ {error}")
        
        st.markdown("---")
        
        st.markdown("""
        <div class="admin-action admin-action-warning">
            <strong>📊 Update Claim Interval</strong>
            <p style="color: #8899aa; font-size: 12px;">Hours between reward claims</p>
        </div>
        """, unsafe_allow_html=True)
        
        current_interval = mining_rate.get('claim_interval_hours', 24) if mining_rate else 24
        new_interval = st.number_input("Claim Interval (hours)", min_value=1, max_value=168, value=int(current_interval))
        
        if st.button("Update Claim Interval", use_container_width=True):
            with st.spinner("Updating..."):
                data, error = api_request('/api/mining/config', 'POST', {"claim_interval_hours": new_interval})
                if data and not error:
                    st.success(f"✅ Claim interval updated to {new_interval} hours")
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
        
        stats_data, _ = api_request('/api/stats')
        if stats_data:
            st.metric("Total Supply", f"{stats_data.get('total_supply', 0):.4f} {TOKEN_SYMBOL}")
            st.metric("Circulating Supply", f"{stats_data.get('circulating_supply', 0):.4f} {TOKEN_SYMBOL}")
            st.metric("Total Wallets", stats_data.get('total_wallets', 0))
            st.metric("Total Transactions", stats_data.get('total_transactions', 0))
            st.metric("Max Supply", f"{stats_data.get('max_supply', 100000000):,} {TOKEN_SYMBOL}")
            st.metric("Mining Rate", f"{stats_data.get('hourly_mining_rate', 0.5)} {TOKEN_SYMBOL}/hr")
        
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
# TAB 6: WALLETS
# ============================================
with tab6:
    st.subheader("👛 Wallet Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="admin-action admin-action-success">
            <strong>🆕 Create New Wallet</strong>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🪙 Create Wallet", use_container_width=True, type="primary"):
            with st.spinner("Creating wallet..."):
                data, error = api_request('/api/wallet/create', 'POST')
                if data and not error:
                    st.success("✅ Wallet created successfully!")
                    st.info(f"""
                    **Address:** `{data.get('address')}`  
                    **Private Key:** `{data.get('private_key')}`  
                    **Balance:** 0 {TOKEN_SYMBOL}
                    """)
                    refresh_data()
                else:
                    st.error(f"❌ {error}")
    
    with col2:
        st.markdown("""
        <div class="admin-action admin-action-warning">
            <strong>🔍 Lookup Wallet</strong>
        </div>
        """, unsafe_allow_html=True)
        
        lookup_address = st.text_input("Enter Wallet Address", placeholder="0x...")
        
        if lookup_address and st.button("🔍 Lookup", use_container_width=True):
            with st.spinner("Looking up..."):
                balance_data, _ = api_request(f'/api/balance/{lookup_address}')
                stats_data, _ = api_request(f'/api/mining/stats/{lookup_address}')
                
                if balance_data:
                    st.success("✅ Wallet found!")
                    st.info(f"""
                    **Address:** `{lookup_address}`  
                    **Balance:** {balance_data.get('balance', 0):.6f} {TOKEN_SYMBOL}
                    """)
                    
                    if stats_data and not stats_data.get('error'):
                        st.info(f"""
                        **Total Mined:** {stats_data.get('total_mined', 0):.6f} {TOKEN_SYMBOL}  
                        **Mining Active:** {'🟢 Yes' if stats_data.get('mining_active') else '🔴 No'}
                        """)
                else:
                    st.warning("⚠️ Wallet not found")

# ============================================
# FOOTER
# ============================================
st.markdown(f"""
<div class="footer">
    <p>⚙️ <b>{APP_NAME}</b> · {TOKEN_SYMBOL} Blockchain Monitor</p>
    <p style="font-size: 11px; color: #445566;">
        API: {API_URL} · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </p>
</div>
""", unsafe_allow_html=True)
