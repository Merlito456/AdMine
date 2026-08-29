class Blockchain:
    def __init__(self):
        self.difficulty = int(os.getenv('DIFFICULTY', 4))
        self.mining_reward = float(os.getenv('MINING_REWARD', 10))
        self.ad_reward = float(os.getenv('AD_REWARD', 0.5))
        
        # ============================================
        # SUPPLY TRACKING (Blockchain Level)
        # ============================================
        self.total_supply = 0  # Track at blockchain level
        self.circulating_supply = 0  # In active wallets
        self.burned_supply = 0  # Burned tokens
        self.minted_supply = 0  # Minted tokens
        self.genesis_supply = 0  # Initial supply
        self.max_supply = 100_000_000  # Max ADT tokens
        
        self.chain = []
        self.pending_transactions = []
        
        # Load from Supabase or create genesis
        self.load_from_db()
    
    def create_genesis_block(self):
        """Create and save genesis block with initial supply"""
        print("🚀 Creating genesis block...")
        
        # Set initial supply (e.g., 10,000 ADT for testing)
        self.genesis_supply = 10000
        self.total_supply = self.genesis_supply
        self.circulating_supply = self.genesis_supply
        
        # Create genesis transactions
        genesis_transactions = [
            {
                "from": "system",
                "to": "admin_wallet",
                "amount": self.genesis_supply,
                "type": "genesis",
                "token": TOKEN_SYMBOL,
                "timestamp": time.time()
            }
        ]
        
        genesis_block = Block(0, genesis_transactions, time.time(), "0")
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
        
        # Save to Supabase
        if supabase:
            self.save_block_to_db(genesis_block)
            # Create initial wallet with genesis supply
            self.update_wallet_balance("admin_wallet", self.genesis_supply)
        
        # Create system wallets
        self.create_system_wallets()
        
        # Save supply data to config
        self.save_supply_config()
        
        print(f"✅ Genesis block created! Total Supply: {self.total_supply} {TOKEN_SYMBOL}")
    
    def save_supply_config(self):
        """Save supply data to Supabase config"""
        if not supabase:
            return
            
        try:
            config_data = {
                "key": "supply_data",
                "value": json.dumps({
                    "total_supply": self.total_supply,
                    "circulating_supply": self.circulating_supply,
                    "burned_supply": self.burned_supply,
                    "minted_supply": self.minted_supply,
                    "genesis_supply": self.genesis_supply,
                    "max_supply": self.max_supply,
                    "updated_at": datetime.utcnow().isoformat()
                })
            }
            supabase.table('config').upsert(config_data).execute()
        except Exception as e:
            print(f"⚠️ Error saving supply config: {e}")
    
    def load_supply_config(self):
        """Load supply data from Supabase config"""
        if not supabase:
            return
            
        try:
            response = supabase.table('config').select('*').eq('key', 'supply_data').execute()
            if response.data:
                supply_data = json.loads(response.data[0]['value'])
                self.total_supply = supply_data.get('total_supply', 0)
                self.circulating_supply = supply_data.get('circulating_supply', 0)
                self.burned_supply = supply_data.get('burned_supply', 0)
                self.minted_supply = supply_data.get('minted_supply', 0)
                self.genesis_supply = supply_data.get('genesis_supply', 0)
                self.max_supply = supply_data.get('max_supply', 100_000_000)
        except Exception as e:
            print(f"⚠️ Error loading supply config: {e}")
    
    def mint_tokens(self, address, amount):
        """Mint new tokens (increases total supply)"""
        if self.total_supply + amount > self.max_supply:
            return {"error": f"Cannot mint: Would exceed max supply of {self.max_supply}"}
        
        # Update supply at blockchain level
        self.total_supply += amount
        self.circulating_supply += amount
        self.minted_supply += amount
        
        # Create mint transaction
        transaction = {
            "from": "system",
            "to": address,
            "amount": amount,
            "type": "mint",
            "token": TOKEN_SYMBOL,
            "timestamp": time.time()
        }
        
        self.add_transaction(transaction)
        self.save_supply_config()
        
        return {
            "status": "success",
            "amount": amount,
            "total_supply": self.total_supply,
            "circulating_supply": self.circulating_supply
        }
    
    def burn_tokens(self, address, amount):
        """Burn tokens (decreases total supply)"""
        # Check if address has enough balance
        balance = self.get_balance(address)
        if balance < amount:
            return {"error": f"Insufficient balance: {balance} < {amount}"}
        
        # Update supply at blockchain level
        self.total_supply -= amount
        self.circulating_supply -= amount
        self.burned_supply += amount
        
        # Create burn transaction
        transaction = {
            "from": address,
            "to": "system",
            "amount": amount,
            "type": "burn",
            "token": TOKEN_SYMBOL,
            "timestamp": time.time()
        }
        
        self.add_transaction(transaction)
        self.save_supply_config()
        
        return {
            "status": "success",
            "amount": amount,
            "total_supply": self.total_supply,
            "circulating_supply": self.circulating_supply
        }
    
    def mine_pending_transactions(self, mining_reward_address):
        """Mine pending transactions"""
        if not self.pending_transactions:
            return None
        
        # Check if mining reward would exceed max supply
        if self.total_supply + self.mining_reward > self.max_supply:
            print(f"⚠️ Cannot mine: Would exceed max supply of {self.max_supply}")
            return None
        
        # Add mining reward
        reward_tx = {
            "from": "system",
            "to": mining_reward_address,
            "amount": self.mining_reward,
            "type": "mining_reward",
            "token": TOKEN_SYMBOL,
            "timestamp": time.time()
        }
        self.pending_transactions.append(reward_tx)
        
        # Update supply at blockchain level
        self.total_supply += self.mining_reward
        self.circulating_supply += self.mining_reward
        
        # Create block
        block = Block(
            index=len(self.chain),
            transactions=self.pending_transactions,
            timestamp=time.time(),
            previous_hash=self.chain[-1].hash
        )
        
        # Mine
        block.mine_block(self.difficulty)
        self.chain.append(block)
        
        # Save to Supabase
        if supabase:
            self.save_block_to_db(block)
            
            # Update pending transactions with block index
            for tx in self.pending_transactions:
                try:
                    tx_hash = self.generate_tx_hash(tx)
                    supabase.table('transactions').update({'block_index': block.index}).eq('tx_hash', tx_hash).execute()
                except Exception as e:
                    print(f"⚠️ Error updating transaction: {e}")
        
        # Update wallet balances
        for tx in self.pending_transactions:
            if tx.get('to') and tx['to'] not in ['system', 'ad_system']:
                self.update_wallet_balance(tx['to'], tx.get('amount', 0))
            if tx.get('from') and tx['from'] not in ['system', 'ad_system']:
                self.update_wallet_balance(tx['from'], -tx.get('amount', 0))
        
        self.pending_transactions = []
        self.save_supply_config()
        
        return block
    
    def get_blockchain_stats(self):
        """Get blockchain statistics (UPDATED)"""
        stats = {
            'total_blocks': len(self.chain),
            'total_transactions': 0,
            'total_wallets': 0,
            'total_supply': self.total_supply,  # FROM BLOCKCHAIN LEVEL
            'circulating_supply': self.circulating_supply,
            'burned_supply': self.burned_supply,
            'minted_supply': self.minted_supply,
            'genesis_supply': self.genesis_supply,
            'max_supply': self.max_supply
        }
        
        if not supabase:
            return stats
            
        try:
            # Get transactions count
            tx_resp = supabase.table('transactions').select('*', count='exact').execute()
            stats['total_transactions'] = len(tx_resp.data) if hasattr(tx_resp, 'data') else 0
            
            # Get wallets count
            wallet_resp = supabase.table('wallets').select('*', count='exact').execute()
            stats['total_wallets'] = len(wallet_resp.data) if hasattr(wallet_resp, 'data') else 0
            
        except Exception as e:
            print(f"⚠️ Error getting stats: {e}")
            
        return stats
    
    def get_token_info(self):
        """Get token information (UPDATED)"""
        stats = self.get_blockchain_stats()
        return {
            "name": TOKEN_NAME,
            "symbol": TOKEN_SYMBOL,
            "decimals": TOKEN_DECIMALS,
            "total_supply": stats['total_supply'],
            "circulating_supply": stats['circulating_supply'],
            "burned_supply": stats['burned_supply'],
            "minted_supply": stats['minted_supply'],
            "genesis_supply": stats['genesis_supply'],
            "max_supply": stats['max_supply'],
            "mining_reward": self.mining_reward,
            "ad_reward": self.ad_reward,
            "difficulty": self.difficulty
        }
