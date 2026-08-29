import streamlit as st
import requests
import json
import time
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import os

# Configuration
API_URL = os.getenv('API_URL', 'http://localhost:5000')
TOKEN_SYMBOL = "ADT"
APP_NAME = "AdMine"

# Page config
st.set_page_config(
    page_title=f"{APP_NAME} - {TOKEN_SYMBOL} Mining",
    page_icon="⛓️",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 30px;
    }
    .token-info {
        background: #0f3460;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #e94560;
    }
    .reward-box {
        background: #16213e;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'wallet_address' not in st.session_state:
    st.session_state.wallet_address = None
if 'balance' not in st.session_state:
    st.session_state.balance = 0

def make_api_request(endpoint, method='GET', data=None):
    """Make API request to backend"""
    try:
        url = f"{API_URL}{endpoint}"
        if method == 'GET':
            response = requests.get(url, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=10)
        else:
            return None, "Unsupported method"
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Error: {response.status_code}"
    except Exception as e:
        return None, f"Connection error: {str(e)}"

def main():
    # Header
    st.markdown(f"""
    <div class="main-header">
        <h1 style="color: #e94560; margin: 0;">⛓️ {APP_NAME}</h1>
        <p style="color: #8899aa; margin: 5px 0 0 0;">Mine {TOKEN_SYMBOL} tokens while watching ads</p>
    </div>
    """, unsafe_allow_html=True)

    # Get token info
    token_info, error = make_api_request('/api/token-info')
    
    if token_info:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 Token", f"{token_info.get('symbol', TOKEN_SYMBOL)}")
        with col2:
            st.metric("📊 Total Supply", f"{token_info.get('total_supply', 0):,.0f}")
        with col3:
            st.metric("🔄 Circulating", f"{token_info.get('circulating_supply', 0):,.0f}")
        with col4:
            st.metric("⛏️ Mining Reward", f"{token_info.get('mining_reward', 10)} {TOKEN_SYMBOL}")
    else:
        st.warning("⚠️ Backend not connected. Please ensure the backend is running.")

    st.markdown("---")

    # Sidebar - Wallet Management
    with st.sidebar:
        st.header(f"💰 {TOKEN_SYMBOL} Wallet")
        
        # Create new wallet
        if st.button("🆕 Create New Wallet", use_container_width=True):
            with st.spinner("Creating wallet..."):
                data, error = make_api_request('/api/wallet/create', 'POST')
                if data and not error:
                    st.session_state.wallet_address = data['address']
                    st.session_state.private_key = data['private_key']
                    st.success(f"✅ Wallet Created!")
                    st.info(f"Address: {data['address'][:15]}...")
                    st.code(f"Private Key: {data['private_key'][:20]}...")
                else:
                    st.error(f"Failed: {error}")

        # Import wallet
        st.subheader("🔑 Import Wallet")
        imported_address = st.text_input(f"Enter {TOKEN_SYMBOL} address")
        if st.button("Import", use_container_width=True):
            if imported_address:
                st.session_state.wallet_address = imported_address
                st.success("Wallet imported!")

        # Display wallet info
        if st.session_state.wallet_address:
            st.markdown("---")
            st.subheader(f"📊 {TOKEN_SYMBOL} Wallet Info")
            st.info(f"Address: {st.session_state.wallet_address[:15]}...")
            
            # Get balance
            data, error = make_api_request(f'/api/balance/{st.session_state.wallet_address}')
            if data and not error:
                st.session_state.balance = data['balance']
                st.metric(f"💰 {TOKEN_SYMBOL} Balance", f"{data['balance']:.2f}")
            
            # Staking info
            st.markdown("---")
            st.subheader("📈 Mining Stats")
            st.metric("Block Reward", f"10 {TOKEN_SYMBOL}")
            st.metric("Ad Reward", f"0.5 {TOKEN_SYMBOL}")

    # Main Content
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("⛏️ Mining Center")
        
        # Ad Viewing Mining
        st.subheader("📺 Mine by Viewing Ads")
        st.info(f"Watch ads to earn {TOKEN_SYMBOL} tokens!")
        
        # Simulate ad viewing
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            if st.button("🎬 Watch 15s Ad", use_container_width=True):
                if not st.session_state.wallet_address:
                    st.error("Please create/import a wallet first!")
                else:
                    with st.spinner("Watching ad..."):
                        time.sleep(2)
                        data, error = make_api_request(
                            '/api/ad-reward',
                            'POST',
                            {"wallet_address": st.session_state.wallet_address}
                        )
                        if data and not error:
                            st.success(f"✅ Earned {data['reward']} {TOKEN_SYMBOL}!")
                            st.balloons()
                            data, _ = make_api_request(f'/api/balance/{st.session_state.wallet_address}')
                            if data:
                                st.session_state.balance = data['balance']
                        else:
                            st.error(f"Failed: {error}")

        with col_btn2:
            if st.button("🎬 Watch 30s Ad (2x)", use_container_width=True):
                if not st.session_state.wallet_address:
                    st.error("Please create/import a wallet first!")
                else:
                    with st.spinner("Watching ad..."):
                        time.sleep(3)
                        for _ in range(2):
                            data, error = make_api_request(
                                '/api/ad-reward',
                                'POST',
                                {"wallet_address": st.session_state.wallet_address}
                            )
                        st.success(f"✅ Earned 1.0 {TOKEN_SYMBOL}!")
                        data, _ = make_api_request(f'/api/balance/{st.session_state.wallet_address}')
                        if data:
                            st.session_state.balance = data['balance']

        with col_btn3:
            if st.button("⛏️ Mine Block", use_container_width=True):
                if not st.session_state.wallet_address:
                    st.error("Please create/import a wallet first!")
                else:
                    with st.spinner("Mining block..."):
                        data, error = make_api_request(
                            '/api/mine',
                            'POST',
                            {"address": st.session_state.wallet_address}
                        )
                        if data and not error:
                            st.success(f"✅ Block mined! Earned 10 {TOKEN_SYMBOL}!")
                            data, _ = make_api_request(f'/api/balance/{st.session_state.wallet_address}')
                            if data:
                                st.session_state.balance = data['balance']
                        else:
                            st.error(f"Failed: {error}")

        # Show pending transactions
        st.subheader("📝 Pending Transactions")
        data, error = make_api_request('/api/blockchain')
        if data and not error:
            pending = data.get('pending_transactions', [])
            if pending:
                for tx in pending[:5]:
                    st.info(f"{tx['from'][:10]} → {tx['to'][:10]}: {tx['amount']} {TOKEN_SYMBOL}")
            else:
                st.info("No pending transactions")

    with col2:
        st.header("📊 Blockchain Explorer")
        
        # Blockchain stats
        data, error = make_api_request('/api/blockchain')
        if data and not error:
            chain = data.get('chain', [])
            st.metric("Block Height", len(chain))
            st.metric("Difficulty", data.get('difficulty', 4))
            st.metric("Total Transactions", sum(len(block['transactions']) for block in chain))
            
            # Latest block
            st.subheader("🔗 Latest Block")
            if chain:
                latest = chain[-1]
                st.json({
                    "Index": latest['index'],
                    "Hash": latest['hash'][:20] + "..." if latest.get('hash') else "N/A",
                    "Previous Hash": latest['previous_hash'][:20] + "..." if latest.get('previous_hash') else "N/A",
                    "Transactions": len(latest['transactions']),
                    "Nonce": latest['nonce']
                })
        
        # Verify blockchain
        if st.button("✅ Verify Chain", use_container_width=True):
            data, error = make_api_request('/api/verify-chain')
            if data and not error:
                if data['valid']:
                    st.success("✅ Blockchain is valid!")
                else:
                    st.error("❌ Blockchain is invalid!")

    # Blockchain Visualization
    st.markdown("---")
    st.header("📋 Blockchain Overview")
    
    data, error = make_api_request('/api/blockchain')
    if data and not error:
        chain = data.get('chain', [])
        
        blocks_data = []
        for block in chain[-10:]:
            blocks_data.append({
                "Block": block['index'],
                "Hash": block['hash'][:10] + "..." if block.get('hash') else "N/A",
                "Previous": block['previous_hash'][:10] + "..." if block.get('previous_hash') else "N/A",
                "Transactions": len(block['transactions']),
                "Nonce": block['nonce'],
                "Timestamp": datetime.fromtimestamp(block['timestamp']).strftime('%H:%M:%S')
            })
        
        if blocks_data:
            df = pd.DataFrame(blocks_data)
            st.dataframe(df, use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: #8899aa;">
        🔗 <b>{APP_NAME} v1.0</b> | {TOKEN_SYMBOL} Token | Built with ❤️
        <br>
        <span style="font-size: 12px;">Mine {TOKEN_SYMBOL} by watching ads and contributing to the blockchain</span>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
