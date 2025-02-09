import os
import json
import sys
import time
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from web3 import Web3
import logging



# Load environment variables
load_dotenv()

# AI Model Setup (Gemini AI)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Alchemy API Key
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")

# Base Sepolia RPC URL
RPC_URL = f"https://base-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}"

# Wallet credentials
BPRIVATE_KEY = os.getenv("BPRIVATE_KEY")

# Ensure PRIVATE_KEY is provided
if not BPRIVATE_KEY:
    sys.exit("Error: Private key not found in environment variables.")

# Web3 Setup
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# Ensure Web3 is connected
if not web3.is_connected():
    sys.exit("Error: Unable to connect to Base Sepolia network.")

# Get wallet address from private key
try:
    wallet_address = web3.eth.account.from_key(BPRIVATE_KEY).address
except Exception as e:
    print(f"Wallet Load Failed: {e}")
    sys.exit(1)

def extract_transaction_details(user_input):
    """ Extracts transaction details only if 'Base' is mentioned. """
    if "base" not in user_input.lower():
        return None

    try:
        model = genai.GenerativeModel("gemini-pro")
        prompt = f"""
        Extract the ETH amount and recipient address from this request:
        
        **Input:** {user_input}
        
        **Response Format (strict JSON only, no extra text):**
        {{ "amount": "value", "address": "recipient" }}
        """
        response = model.generate_content(prompt)

        if not response or not response.text:
            print("AI Response Error: No response received.")
            return None

        try:
            result = json.loads(response.text.strip())
        except json.JSONDecodeError:
            print(f"AI Response Error: Not valid JSON → {response.text}")
            return None

        if "amount" not in result or "address" not in result:
            print(f"Missing 'amount' or 'address' in response → {result}")
            return None

        try:
            result["amount"] = float(result["amount"])
        except ValueError:
            print(f"Invalid amount format → {result['amount']}")
            return None

        return result
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def wait_for_confirmation(web3, tx_hash, max_retries=20):
    """Waits for a transaction to be confirmed on the blockchain."""
    retries = 0
    while retries < max_retries:
        try:
            tx_receipt = web3.eth.get_transaction_receipt(tx_hash)
            if tx_receipt:
                if tx_receipt.status == 1:
                    print(f"Transaction Confirmed! Hash: {tx_hash.hex()}")
                else:
                    print(f"Transaction Failed! Hash: {tx_hash.hex()}")
                return tx_receipt
        except Exception:
            print(f"Waiting for confirmation... ({retries + 1}/{max_retries})")

        retries += 1
        time.sleep(5)

    print(f"Transaction not found after {max_retries * 5} seconds. Check manually:")
    print(f"Explorer: https://sepolia.basescan.org/tx/{tx_hash.hex()}")
    return None

def send_transaction(to_address, amount):
    """ Sends a signed transaction on Base Sepolia. """
    try:
        print(f"Sending {amount} ETH to {to_address}...")

        nonce = web3.eth.get_transaction_count(wallet_address)
        gas_price = web3.eth.gas_price
        value = web3.to_wei(float(amount), 'ether')

        tx = {
            'from': wallet_address,
            'to': Web3.to_checksum_address(to_address),
            'value': value,
            'gas': 21000,
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': 84532
        }

        signed_tx = web3.eth.account.sign_transaction(tx, BPRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        print(f"Transaction Sent! Hash: {tx_hash.hex()}")
        print(f"Explorer: https://sepolia.basescan.org/tx/{tx_hash.hex()}")

        wait_for_confirmation(web3, tx_hash)
        
    except Exception as e:
        print(f"Transaction Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
        transaction = extract_transaction_details(user_input)
        if transaction:
            send_transaction(transaction["address"], transaction["amount"])
        
    else:
        print("No input provided. Exiting.")
