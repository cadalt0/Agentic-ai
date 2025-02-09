import os
import json
import sys
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from web3 import Web3
import logging

# Suppress all logs and errors
sys.stderr = open(os.devnull, "w")
sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
logging.basicConfig(level=logging.CRITICAL)

# Load environment variables once
load_dotenv()

# AI Model Setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Ethereum Sepolia RPC URL
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
RPC_URL = f"https://eth-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}"

# Wallet credentials
EPRIVATE_KEY = os.getenv("EPRIVATE_KEY")

# Web3 Setup (Load Wallet Only Once)
web3 = Web3(Web3.HTTPProvider(RPC_URL))
try:
    WALLET_ADDRESS = web3.eth.account.from_key(EPRIVATE_KEY).address
except Exception as e:
    print(f"Wallet Load Failed: {e}")
    sys.exit(1)  # Exit if wallet fails to load

def ai_process_request(user_input):
    """ Process AI request and execute transaction if needed. """
    try:
        model = genai.GenerativeModel("gemini-pro")
        prompt = f"""
        You handle Ethereum Sepolia transactions and a helpful freind who answers queries.
        - If the user asks a general question, reply normally.
        - DONT RESPOND IF USER ASK FOR SWAP token OR SWAPPING token , you can answer if he ask query related to swapping tokens.
        - [DONT RESPOND ]ignore transaction requests if mention of 'Base', 'Arbitrum'. dont extract details for these just send reply "being excucted note: can take some time to appear in your wallet"
        - If they request a transaction (e.g., "Send 0.5 ETH to 0x123..."), extract details.

        **Response format:**
        - If transaction: {{ "type": "transaction", "amount": "value", "address": "recipient" }}
        - If general query: {{ "type": "general", "response": "Your reply here" }}

        **User Input:** {user_input}
        """
        response = model.generate_content(prompt)

        if response and response.text:
            try:
                result = json.loads(response.text.strip())
                if result.get("type") == "transaction":
                    send_transaction(result.get("address"), result.get("amount"))
                else:
                    print(f": {result['response']}")
            except Exception as e:
                print(f"AI Processing Error: {e}")
        else:
            print("AI Error: No valid response")
    except Exception as e:
        print(f"AI Request Failed: {e}")

def send_transaction(to_address, amount):
    """ Send ETH transaction with estimated gas. """
    try:
        nonce = web3.eth.get_transaction_count(WALLET_ADDRESS)
        gas_price = web3.eth.gas_price
        value = web3.to_wei(amount, 'ether')

        # **Estimate Gas**
        estimated_gas = web3.eth.estimate_gas({
            'from': WALLET_ADDRESS,
            'to': Web3.to_checksum_address(to_address),
            'value': value
        })

        tx = {
            'from': WALLET_ADDRESS,
            'to': Web3.to_checksum_address(to_address),
            'value': value,
            'gas': estimated_gas,  # **Fix: Use estimated gas**
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': 11155111
        }

        signed_tx = web3.eth.account.sign_transaction(tx, EPRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        print(f"Transaction Sent! TX Hash: https://sepolia.etherscan.io/tx/0x{tx_hash.hex()}")

    except Exception as e:
        print(f"Transaction Failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
        ai_process_request(user_input)
    else:
        print("...")
