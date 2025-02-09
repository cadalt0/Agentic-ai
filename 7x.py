import os
import json
import time
from dotenv import load_dotenv
from web3 import Web3
import google.generativeai as genai

# Load environment variables
load_dotenv()

# AI Setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-pro")

# Web3 Setup
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
RPC_URL = f"https://unichain-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
web3 = Web3(Web3.HTTPProvider(RPC_URL))

if not web3.is_connected():
    exit("❌ Failed to connect to UniChain Sepolia.")

UPRIVATE_KEY = os.getenv("UPRIVATE_KEY")
wallet_address = web3.eth.account.from_key(UPRIVATE_KEY).address

# Contract Addresses
UNISWAP_ROUTER = web3.to_checksum_address("0x920b806E40A00E02E7D2b94fFc89860fDaEd3640")
WETH_ADDRESS = web3.to_checksum_address("0x4200000000000000000000000000000000000006")

# Tokens List
TOKENS = {
    "bkga": web3.to_checksum_address("0x2769078273c29AfC6A21BF8B64368CC5d1972C6A"),
    "gaokub": web3.to_checksum_address("0x84566e3686476fd53F3ee8e8333F991B7383355A")
}

# Uniswap Router ABI
UNISWAP_ROUTER_ABI = '[{"inputs":[{"name":"amountIn","type":"uint256"},{"name":"amountOutMin","type":"uint256"},{"name":"path","type":"address[]"},{"name":"to","type":"address"},{"name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"amountOutMin","type":"uint256"},{"name":"path","type":"address[]"},{"name":"to","type":"address"},{"name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"}]'

uniswap_router = web3.eth.contract(address=UNISWAP_ROUTER, abi=json.loads(UNISWAP_ROUTER_ABI))

def ai_understand_swap(user_input):
    """AI detects if the input requests a token swap."""
    prompt = f'''
    Extract swap details from the input.
    - Identify the amount to swap.
    - Identify the token name being swapped from (must be "eth", "bkga", or "gaokub").
    - Identify the token name being swapped to (must be "eth", "bkga", or "gaokub").
    - Ensure that "eth" is correctly detected when mentioned.
    
    **Input:** {user_input}
    **Response Format:** {{ "amount": "value", "token_from": "name", "token_to": "name" }}
    '''
    
    response = model.generate_content(prompt)
    try:
        swap_data = json.loads(response.text)
        return float(swap_data["amount"]), swap_data["token_from"].lower(), swap_data["token_to"].lower()
    except:
        return None, None, None

def swap_token(amount, token_from, token_to):
    """Swaps a token for another token or ETH and returns transaction details."""
    amount_in_wei = web3.to_wei(amount, 'ether')
    
    token_from_address = TOKENS.get(token_from, WETH_ADDRESS if token_from == "eth" else None)
    token_to_address = TOKENS.get(token_to, WETH_ADDRESS if token_to == "eth" else None)
    
    if not token_from_address or not token_to_address:
        return "❌ Invalid token!"
    
    path = [token_from_address, token_to_address]
    amount_out_min = 0  # Ideally, fetch min output dynamically
    deadline = int(time.time()) + 600
    nonce = web3.eth.get_transaction_count(wallet_address, 'pending')

    if token_from == "eth":
        tx = uniswap_router.functions.swapExactETHForTokens(
            amount_out_min, path, wallet_address, deadline
        ).build_transaction({
            'from': wallet_address,
            'value': amount_in_wei,
            'nonce': nonce
        })
    else:
        token_contract = web3.eth.contract(address=token_from_address, abi=[
            {"name": "approve", "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "type": "function"}
        ])
        
        approve_tx = token_contract.functions.approve(UNISWAP_ROUTER, amount_in_wei).build_transaction({
            'from': wallet_address,
            'nonce': nonce
        })
        signed_approve_tx = web3.eth.account.sign_transaction(approve_tx, UPRIVATE_KEY)
        web3.eth.send_raw_transaction(signed_approve_tx.raw_transaction)

        # Wait for approval confirmation
        web3.eth.wait_for_transaction_receipt(signed_approve_tx.hash)

        # Increment nonce for the swap
        nonce = web3.eth.get_transaction_count(wallet_address, 'pending')

        tx = uniswap_router.functions.swapExactTokensForTokens(
            amount_in_wei, amount_out_min, path, wallet_address, deadline
        ).build_transaction({
            'from': wallet_address,
            'nonce': nonce
        })

    signed_tx = web3.eth.account.sign_transaction(tx, UPRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    if tx_receipt and tx_receipt.status == 1:
        return f" Swap Successful! Transaction: {tx_hash.hex()}"
    else:
        return f"❌ Swap Failed! Transaction: {tx_hash.hex()}"


import sys

if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:]).lower()
        amount, token_from, token_to = ai_understand_swap(user_input)
        
        if amount and token_from and token_to:
            status_message = swap_token(amount, token_from, token_to)
            print(status_message)
        else:
            print("❌ Invalid command! Example: swap 100 bkga for gaokub")
    else:
        print("❌ No command received! Please provide input.")
