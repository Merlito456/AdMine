import streamlit as st
import requests
import json
import time
from datetime import datetime
import os
import pandas as pd

# ============================================
# CONFIGURATION
# ============================================
API_URL = os.getenv('API_URL', 'http://localhost:5000')
TOKEN_SYMBOL = "ADT"
APP_NAME = "AdMine"

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title=f"{APP_NAME} - {TOKEN_SYMBOL}",
    page_icon="⛓️",
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
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    
    /* Cards */
    .stat-card {
        background: linear-gradient(145deg, #1e1e2f, #2d2d44);
        padding: 20px;
        border-radius: 12px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        margin-bottom: 15px;
    }
    
    .stat-card-blue { border-left-color: #667eea; }
    .stat-card-green { border-left-color: #00d2ff; }
    .stat-card-orange { border-left-color: #f093fb; }
    .stat-card-pink { border-left-color: #f5576c; }
    
    .stat-number {
        font-size: 32px;
        font-weight: bold;
        color: #ffffff;
        margin: 5px 0;
    }
    
    .stat-label {
        font-size: 14px;
        color: #8899aa;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .stat-change {
        font-size: 12px;
        color: #00d2ff;
    }
    
    /* Buttons */
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* Info boxes */
    .info-box {
        background: rgba(102, 126, 234, 0.1);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(102, 126, 234, 0.2);
    }
    
    /* Wallet display */
    .wallet-display {
        background: #1a1a2e;
        padding: 15px;
        border-radius: 10px;
        font-family: monospace;
        font-size: 14px;
        color: #00d2ff;
        word-break: break-all;
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
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 20px;
        color: #8899aa;
        font-size: 12px;
        border-top: 1px solid #2d2d44;
        margin-top: 40px;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================
# API HELPER FUNCTIONS
# ============================================
def api_request(endpoint, method='GET', data=None):
    """Make API request to backend"""
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

# ============================================
# SESSION STATE INIT
# ============================================
if 'wallet' not in st.session_state:
    st.session_state.wallet = None
if 'balance' not in st.session_state:
    st.session_state.balance = 0
if 'token_info' not in st.session_state:
    st.session_state.token_info = None

# ============================================
# HEADER
# ============================================
st.markdown(f"""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="color: white; margin: 0; font-size: 36px;">⛓️ {APP_NAME}</h1>
            <p style="color: rgba(255,255,255,0.8); margin: 5px 0 0 0; font-size: 16px;">
                Proof of System · {TOKEN_SYMBOL} Token
            </p>
        </div>
        <div style="text-align: right;">
            <span style="color: rgba(255,255,255,0.6); font-size: 12px;">STATUS</span><br>
            <span id="status" class="status-online">● ONLINE</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================
# SYSTEM STATS ROW
# ============================================
st.subheader("📊 System Overview")

# Check backend
backend_data, backend_error = api_request('/api/token-info')

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if backend_data:
        st.markdown(f"""
        <div class="stat-card stat-card-blue">
            <div class="stat-label">🪙 Token</div>
            <div class="stat-number">{backend_data.get('symbol', TOKEN_SYMBOL)}</div>
            <div class="stat-change">{backend_data.get('name', 'AdToken')}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="stat-card stat-card-blue">
            <div class="stat-label">🪙 Token</div>
            <div class="stat-number">OFFLINE</div>
            <div class="stat-change">⚠️ Backend down</div>
        </div>
        """, unsafe_allow_html=True)

with col2:
    supply = backend_data.get('total_supply', 100_000_000) if backend_data else 100_000_000
    st.markdown(f"""
    <div class="stat-card stat-card-green">
        <div class="stat-label">📊 Total Supply</div>
        <div class="stat-number">{supply:,}</div>
        <div class="stat-change">{TOKEN_SYMBOL}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    circ = backend_data.get('circulating_supply', 0) if backend_data else 0
    st.markdown(f"""
    <div class="stat-card stat-card-orange">
        <div class="stat-label">🔄 Circulating</div>
        <div class="stat-number">{circ:,.0f}</div>
        <div class="stat-change">Mined so far</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    reward = backend_data.get('mining_reward', 10) if backend_data else 10
    st.markdown(f"""
    <div class="stat-card stat-card-pink">
        <div class="stat-label">⛏️ Block Reward</div>
        <div class="stat-number">{reward} {TOKEN_SYMBOL}</div>
        <div class="stat-change">Per block</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    ad_reward = backend_data.get('ad_reward', 0.5) if backend_data else 0.5
    st.markdown(f"""
    <div class="stat-card stat-card-blue">
        <div class="stat-label">📺 Ad Reward</div>
        <div class="stat-number">{ad_reward} {TOKEN_SYMBOL}</div>
        <div class="stat-change">Per view</div>
    </div>
    """, unsafe_allow_html=True)

# ============================================
# MAIN CONTENT - 3 COLUMNS
# ============================================
st.markdown("---")

left_col, mid_col, right_col = st.columns([1.2, 1, 0.8])

# ============================================
# LEFT COLUMN - WALLET & MINING
# ============================================
with left_col:
    st.subheader("👛 Wallet")
    
    # Wallet actions
    col_w1, col_w2 = st.columns(2)
    
    with col_w1:
        if st.button("🆕 Create Wallet", use_container_width=True):
            data, error = api_request('/api/wallet/create', 'POST')
            if data and not error:
                st.session_state.wallet = data['address']
                st.session_state.balance = 0
                st.success("✅ Wallet created!")
                st.rerun()
            else:
                st.error(f"❌ {error}")
    
    with col_w2:
        if st.session_state.wallet:
            if st.button("🗑️ Disconnect", use_container_width=True):
                st.session_state.wallet = None
                st.session_state.balance = 0
                st.rerun()
    
    # Wallet display
    if st.session_state.wallet:
        st.markdown(f"""
        <div class="wallet-display">
            📍 {st.session_state.wallet[:18]}...{st.session_state.wallet[-6:]}
        </div>
        """, unsafe_allow_html=True)
        
        # Get balance
        balance_data, _ = api_request(f'/api/balance/{st.session_state.wallet}')
        if balance_data:
            balance = balance_data.get('balance', 0)
            st.session_state.balance = balance
            st.metric(f"💰 {TOKEN_SYMBOL} Balance", f"{balance:.4f}")
        else:
            st.metric(f"💰 {TOKEN_SYMBOL} Balance", "⏳ Loading...")
    else:
        st.info("👆 Create or import a wallet to start mining")
        st.caption("No wallet connected")
    
    st.markdown("---")
    
    # ============================================
    # MINING ACTIONS
    # ============================================
    st.subheader("⛏️ Mining")
    
    # Watch Ad
    st.markdown("### 📺 Watch Ad")
    if st.button("🎬 Watch Ad (+0.5 ADT)", use_container_width=True):
        if not st.session_state.wallet:
            st.warning("⚠️ Connect a wallet first!")
        else:
            with st.spinner("📺 Playing ad..."):
                time.sleep(1.5)
                data, error = api_request(
                    '/api/ad-reward',
                    'POST',
                    {"wallet_address": st.session_state.wallet}
                )
                if data and not error:
                    st.success(f"✅ Earned {data.get('reward', 0.5)} {TOKEN_SYMBOL}!")
                    st.balloons()
                    # Refresh balance
                    b_data, _ = api_request(f'/api/balance/{st.session_state.wallet}')
                    if b_data:
                        st.session_state.balance = b_data.get('balance', 0)
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(f"❌ {error}")
    
    # Mine Block
    st.markdown("### ⛏️ Mine Block")
    if st.button("⛏️ Mine Block (+10 ADT)", use_container_width=True, type="primary"):
        if not st.session_state.wallet:
            st.warning("⚠️ Connect a wallet first!")
        else:
            with st.spinner("⛏️ Mining block..."):
                time.sleep(2)
                data, error = api_request(
                    '/api/mine',
                    'POST',
                    {"address": st.session_state.wallet}
                )
                if data and not error:
                    st.success(f"✅ Block mined! +10 {TOKEN_SYMBOL}!")
                    # Refresh balance
                    b_data, _ = api_request(f'/api/balance/{st.session_state.wallet}')
                    if b_data:
                        st.session_state.balance = b_data.get('balance', 0)
                    st.rerun()
                else:
                    st.error(f"❌ {error}")
    
    # ============================================
    # RECENT ACTIVITY
    # ============================================
    st.markdown("---")
    st.subheader("🔄 Recent Activity")
    
    if st.session_state.wallet:
        # Get recent transactions
        tx_data, _ = api_request(f'/api/wallet/{st.session_state.wallet}/transactions')
        if tx_data:
            txs = tx_data.get('transactions', [])[:5]
            if txs:
                for tx in txs:
                    amount = tx.get('amount', 0)
                    tx_type = tx.get('type', 'transfer')
                    emoji = "📤" if tx.get('from_address') == st.session_state.wallet else "📥"
                    color = "#f5576c" if tx.get('from_address') == st.session_state.wallet else "#00d2ff"
                    st.markdown(f"""
                    <div style="background: #1a1a2e; padding: 8px 12px; border-radius: 8px; margin-bottom: 5px; border-left: 3px solid {color};">
                        <span style="font-size: 13px;">
                            {emoji} {amount} {TOKEN_SYMBOL} 
                            <span style="color: #8899aa; font-size: 11px;">
                                {tx_type.replace('_', ' ').title()}
                            </span>
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("No recent transactions")
        else:
            st.caption("No transactions yet")
    else:
        st.caption("Connect wallet to see activity")

# ============================================
# MIDDLE COLUMN - BLOCKCHAIN EXPLORER
# ============================================
with mid_col:
    st.subheader("🔗 Blockchain")
    
    # Get blockchain data
    chain_data, _ = api_request('/api/blockchain')
    
    if chain_data:
        chain = chain_data.get('chain', [])
        
        # Block height
        st.metric("📏 Block Height", len(chain))
        
        # Difficulty
        st.metric("🎯 Difficulty", chain_data.get('difficulty', 4))
        
        # Latest block
        st.markdown("### 📦 Latest Block")
        if chain:
            latest = chain[-1]
            st.json({
                "Block": latest.get('index', 0),
                "Hash": latest.get('hash', 'N/A')[:12] + "...",
                "Txs": len(latest.get('transactions', [])),
                "Nonce": latest.get('nonce', 0)
            }, expanded=False)
        
        # Pending transactions
        pending = chain_data.get('pending_transactions', [])
        st.markdown(f"### 📝 Pending: {len(pending)}")
        if pending:
            for tx in pending[:3]:
                st.caption(f"{tx.get('from', '')[:8]} → {tx.get('to', '')[:8]}: {tx.get('amount', 0)} {TOKEN_SYMBOL}")
        else:
            st.caption("No pending transactions")
        
        # Validate chain
        if st.button("✅ Verify Chain", use_container_width=True):
            verify_data, _ = api_request('/api/verify-chain')
            if verify_data and verify_data.get('valid'):
                st.success("✅ Blockchain is valid!")
            else:
                st.error("❌ Blockchain verification failed!")
    
    else:
        st.warning("⚠️ Blockchain data unavailable")
        st.caption("Backend may be offline")

# ============================================
# RIGHT COLUMN - TOKEN INFO & STATS
# ============================================
with right_col:
    st.subheader("📈 Token Info")
    
    if backend_data:
        st.markdown(f"""
        <div class="info-box">
            <div style="display: flex; justify-content: space-between; padding: 5px 0;">
                <span style="color: #8899aa;">Name</span>
                <span style="color: white;">{backend_data.get('name', 'AdToken')}</span>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 5px 0; border-top: 1px solid #2d2d44;">
                <span style="color: #8899aa;">Symbol</span>
                <span style="color: #00d2ff; font-weight: bold;">{backend_data.get('symbol', TOKEN_SYMBOL)}</span>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 5px 0; border-top: 1px solid #2d2d44;">
                <span style="color: #8899aa;">Decimals</span>
                <span style="color: white;">{backend_data.get('decimals', 18)}</span>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 5px 0; border-top: 1px solid #2d2d44;">
                <span style="color: #8899aa;">Total Supply</span>
                <span style="color: #f093fb;">{backend_data.get('total_supply', 0):,}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("ℹ️ System Status")
    
    # Backend status
    if backend_data:
        st.success("✅ Backend: Connected")
        st.caption(f"API: {API_URL}")
    else:
        st.error("❌ Backend: Offline")
    
    # Wallet status
    if st.session_state.wallet:
        st.success(f"✅ Wallet: Connected")
    else:
        st.warning("⚠️ Wallet: Not connected")
    
    # Network stats
    st.markdown("---")
    st.subheader("🌐 Network")
    
    if chain_data:
        chain = chain_data.get('chain', [])
        st.caption(f"⛓️ Chain Length: {len(chain)}")
        st.caption(f"⛏️ Mining Reward: {chain_data.get('mining_reward', 10)} {TOKEN_SYMBOL}")
        st.caption(f"📺 Ad Reward: {chain_data.get('ad_reward', 0.5)} {TOKEN_SYMBOL}")

# ============================================
# FOOTER
# ============================================
st.markdown("""
<div class="footer">
    <p>⛓️ <b>AdMine</b> · {TOKEN_SYMBOL} Token · Proof of System</p>
    <p style="font-size: 11px; color: #556677;">
        Built with Streamlit · {API_URL}
    </p>
</div>
""".replace('{TOKEN_SYMBOL}', TOKEN_SYMBOL).replace('{API_URL}', API_URL), unsafe_allow_html=True)

# ============================================
# AUTO-REFRESH (Optional)
# ============================================
if st.session_state.wallet:
    # Auto-refresh balance every 30 seconds
    st.caption("🔄 Auto-refreshing every 30s")
    # Add a refresh button
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()
