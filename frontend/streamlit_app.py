import streamlit as st
import requests
import json
import time
from datetime import datetime
import pandas as pd

# Configuration
API_URL = "https://your-backend.onrender.com"  # Replace with your Render.com URL

st.set_page_config(
    page_title="Blockchain Ecosystem",
    page_icon="⛓️",
    layout="wide"
)

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
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, json=data)
        else:
            return None, "Unsupported method"
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Error: {response.status_code}"
    except Exception as e:
        return None, f"Connection error: {str(e)}"

def main():
    st.title("⛓️ Blockchain Mining Ecosystem")
    st.markdown("---")

    # Sidebar - Wallet Management
    with st.sidebar:
        st.header("💰 Wallet Management")
        
        # Create new wallet
        if st.button("🆕 Create New Wallet", use_container_width=True):
            with st.spinner("Creating wallet..."):
                data, error = make_api_request('/api/wallet/create', 'POST')
                if data and not error:
                    st.session_state.wallet_address = data['address']
                    st.session_state.private_key = data['private_key']
                    st.success(f"✅ Wallet Created!")
                    st.code(f"Address: {data['address'][:10]}...")
                else:
                    st.error(f"Failed: {error}")

        # Import wallet
        st.subheader("🔑 Import Wallet")
        imported_address = st.text_input("Enter wallet address")
        if st.button("Import", use_container_width=True):
            if imported_address:
                st.session_state.wallet_address = imported_address
                st.success("Wallet imported!")

        # Display wallet info
        if st.session_state.wallet_address:
            st.markdown("---")
            st.subheader("📊 Wallet Info")
            st.info(f"Address: {st.session_state.wallet_address[:15]}...")
            
            # Get balance
            data, error = make_api_request(f'/api/balance/{st.session_state.wallet_address}')
            if data and not error:
                st.session_state.balance = data['balance']
                st.metric("Balance", f"{data['balance']:.2f} BLC")
            
            # Staking info
            st.markdown("---")
            st.subheader("📈 Stats")
            st.metric("Mining Reward", "10 BLC")
            st.metric("Ad Reward", "0.5 BLC")

    # Main Content
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("⛏️ Mining Center")
        
        # Ad Viewing Mining
        st.subheader("📺 Mine by Viewing Ads")
        st.info("Watch ads to earn BLC tokens!")
        
        ad_placeholder = st.empty()
        
        # Simulate ad viewing
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            if st.button("🎬 Watch 15s Ad", use_container_width=True):
                if not st.session_state.wallet_address:
                    st.error("Please create/import a wallet first!")
                else:
                    with st.spinner("Watching ad..."):
                        time.sleep(2)  # Simulate ad viewing
                        data, error = make_api_request(
                            '/api/ad-reward',
                            'POST',
                            {"wallet_address": st.session_state.wallet_address}
                        )
                        if data and not error:
                            st.success(f"✅ Earned {data['reward']} BLC!")
                            st.balloons()
                            # Refresh balance
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
                        # Process multiple ads
                        for _ in range(2):
                            data, error = make_api_request(
                                '/api/ad-reward',
                                'POST',
                                {"wallet_address": st.session_state.wallet_address}
                            )
                        st.success("✅ Earned 1.0 BLC!")
                        data, _ = make_api_request(f'/api/balance/{st.session_state.wallet_address}')
                        if data:
                            st.session_state.balance = data['balance']

        with col_btn3:
            if st.button("⛏️ Mine Now", use_container_width=True):
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
                            st.success("✅ Block mined successfully!")
                            data, _ = make_api_request(f'/api/balance/{st.session_state.wallet_address}')
                            if data:
                                st.session_state.balance = data['balance']

        # Show pending transactions
        st.subheader("📝 Pending Transactions")
        data, error = make_api_request('/api/blockchain')
        if data and not error:
            pending = data.get('pending_transactions', [])
            if pending:
                for tx in pending[:5]:
                    st.info(f"{tx['from'][:10]} → {tx['to'][:10]}: {tx['amount']} BLC")
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
                    "Hash": latest['hash'][:20] + "...",
                    "Previous Hash": latest['previous_hash'][:20] + "...",
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
        
        # Create dataframe for visualization
        blocks_data = []
        for block in chain[-10:]:  # Show last 10 blocks
            blocks_data.append({
                "Block": block['index'],
                "Hash": block['hash'][:10] + "...",
                "Previous": block['previous_hash'][:10] + "...",
                "Transactions": len(block['transactions']),
                "Nonce": block['nonce'],
                "Timestamp": datetime.fromtimestamp(block['timestamp']).strftime('%H:%M:%S')
            })
        
        df = pd.DataFrame(blocks_data)
        st.dataframe(df, use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown("🔗 **Blockchain Ecosystem v1.0** | Built with ❤️")

if __name__ == "__main__":
    main()
