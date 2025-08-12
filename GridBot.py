from ast import And, Global
import requests
import time
import hmac
import hashlib
import threading
from urllib.parse import urlencode
import socket
import datetime
import ccxt
import numpy as np
import sys
import traceback
import logging
import urllib3


# Replace with your actual API keys
MEXC_API_KEY = "mx0vgl2SOoSRFhBg0u"
MEXC_API_SECRET = "6723488979744c8a9dc535620c8a5427"

        
PAIR = "BTCUSDC"
ORDER_SIZE = 3  # USD value per order
BTC_SIZE = 0.000013  # USD value per order
SellOrders ={}
BuyOrders ={}
base_spacing = 200
last_spacing = base_spacing  

#global catch error
logging.basicConfig(filename="bot_log.txt", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def global_exception_handler(exctype, value, tb):
    logging.error("Uncaught Exception:", exc_info=(exctype, value, tb))
    print("An unexpected error occurred! Check bot_log.txt for details.")

sys.excepthook = global_exception_handler


def get_mexc_server_time():
    url = "https://api.mexc.com/api/v3/time"
    response = requests.get(url)
    return response.json().get("serverTime")


def get_mexc_price():
    url = f"https://api.mexc.com/api/v3/depth?symbol={PAIR}&limit=1"
    
    try:
        response = requests.get(url, timeout=5)  # Timeout set to 5 seconds
        response.raise_for_status()  # Raises an error for HTTP codes 4xx/5xx
        data = response.json()
        best_bid = float(data['bids'][0][0])  # Highest buy price
        best_ask = float(data['asks'][0][0])  # Lowest sell price
        return best_bid, best_ask
    except requests.exceptions.Timeout:
        print("Timeout error: mexc API took too long to respond.")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    return None, None  # Return None if request fails


# Function to fetch MEXC account balances
def get_mexc_balance():
    url = "https://api.mexc.com/api/v3/account"
    timestamp = get_mexc_server_time()
    query_string = f"timestamp={timestamp}"
    signature = hmac.new(MEXC_API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    headers = {"X-MEXC-APIKEY": MEXC_API_KEY}
    params = {"timestamp": timestamp, "signature": signature, "recvWindow": 5000}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    balances = {asset['asset']: float(asset['free']) for asset in data['balances']}
    return balances.get('USDC', 0), balances.get('BTC', 0)


# Function to place an order on MEXC
def place_mexc_order(side, price, quantity):
    url = "https://api.mexc.com/api/v3/order"
    
    params = {
        "symbol": PAIR,
        "side": side,
        "type": "LIMIT",
        "quantity": BTC_SIZE,
        "price": price,
        "timeInForce": "GTC",
        "timestamp": get_mexc_server_time(),
        "recvWindow": 5000  # Increase recvWindow (default is 500ms)
    }

    query_string = urlencode(params)
    signature = hmac.new(MEXC_API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    
    params["signature"] = signature  # Add signature to params
    
    headers = {
        "X-MEXC-APIKEY": MEXC_API_KEY  # Ensure correct API Key header
    }
    try:
     response = requests.post(url, headers=headers, params=params)  # Send as params, not JSON
     print("MEXC response:", response.status_code, response.text)
     if response.status_code == 200:
        return response.json()
     else:
        print(f"Failed to place {side} order: {response.text}")
        return None
    except Exception as e:
        print(f"Error placing {side} order: {e}")
        return None

        
def sign_request(params, secret_key):
    """ Generate HMAC SHA256 signature """
    query_string = "&".join([f"{key}={params[key]}" for key in sorted(params)])
    signature = hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

def get_open_orders():
    url = "https://api.mexc.com/api/v3/openOrders"
    
    timestamp = get_mexc_server_time()  # Current timestamp in milliseconds
    params = {
        "symbol": PAIR,
        "timestamp": timestamp
    }
    
    params["signature"] = sign_request(params,MEXC_API_SECRET)

    headers = {
        "X-MEXC-APIKEY": MEXC_API_KEY
    }
    try:
      response = requests.get(url, params=params, headers=headers, timeout=5)
      if response.status_code == 200:
        return response.json()
      else:
        print(f"Failed to fetch open orders: {response.text}")
        return {}
    except Exception as e:
        print(f"Error fetching open orders: {e}")
        return {}

# Function to cancel an order
def cancel_order(order_id):
    url = f"https://api.mexc.com/api/v3/order?symbol={PAIR}&orderId={order_id}"
    requests.delete(url, headers={"X-MEXC-APIKEY": MEXC_API_KEY})



def initialOrders():
    # Step 1: Place initial orders
    best_bid, best_ask = get_mexc_price() 
    if best_bid is None or best_ask is None:
        print("Failed to fetch market prices. Skipping initial orders.")
        return

    for x in range(1,50):  
     response= place_mexc_order("BUY", str(best_bid - (x * last_spacing)),str(ORDER_SIZE / best_bid))
     print(response)
     if response and "orderId" in response:
       BuyOrders[response["orderId"]] = best_bid - (x*last_spacing)
    for y in range(1,50):
     response =place_mexc_order("SELL", str(best_ask + (y*last_spacing)),(ORDER_SIZE / best_ask))
     if response and "orderId" in response:
       SellOrders[response["orderId"]] = best_ask + (y*last_spacing)
       
initialOrders()
time.sleep(2)


def fetch_ohlcv():
    url = "https://api.mexc.com/api/v3/klines"
    params = {
        "symbol": PAIR,
        "limit": 14,
        "interval":'15m'
    }

    try:
         response = requests.get(url,params=params, timeout=10)
         response.raise_for_status()  # Raise an error for HTTP issues (e.g., 404, 500)
        
         candles = response.json() 
         #print(candles)
         if not candles or len(candles) == 0:
          print(f"Error: No OHLCV data returned for {symbol} on MEXC.")
          return None

    except Exception as e:
        print(f"Error fetching OHLCV data: {str(e)}")
        return None

    return np.array(candles)[:, 2:5].astype(float)  # Extract High, Low, Close prices

def calculate_atr(ohlcv):
    """Calculate the Average True Range (ATR)"""
    highs, lows, closes = ohlcv[:, 0], ohlcv[:, 1], ohlcv[:, 2]
    
    tr1 = highs - lows
    tr2 = np.abs(highs - np.roll(closes, 1))
    tr3 = np.abs(lows - np.roll(closes, 1))
    
    tr = np.maximum(tr1, np.maximum(tr2, tr3))[1:]
    atr = np.mean(tr)  # Simple Moving Average ATR
    return atr

def adjust_grid_spacing(base_spacing, atr, atr_avg):
    """Adjust grid spacing based on ATR"""
    return base_spacing * (1 + (atr / atr_avg))

def update_grid_orders(symbol, new_spacing):
    global last_spacing
    
    if new_spacing != last_spacing:
        print(f"Grid spacing changed from {last_spacing} to {new_spacing}, updating orders...")

        # Step 1: Cancel all existing grid orders
        try:
            url = "https://api.mexc.com/api/v3/openOrders"    
            timestamp = get_mexc_server_time()  # Current timestamp in milliseconds
            params = {
                "symbol": symbol,
                "timestamp": timestamp
            }    
            params["signature"] = sign_request(params,MEXC_API_SECRET)
            headers = {"X-MEXC-APIKEY": MEXC_API_KEY}    
            response = requests.delete(url, params=params, headers=headers)
            data = response.json() 
            global BuyOrders 
            BuyOrders = {}
            global SellOrders 
            SellOrders = {} 
            last_spacing = new_spacing
            initialOrders()
            
        except Exception as e:            
            print(f"Error canceling orders: {str(e)}")
       
    else:
        print("Grid spacing unchanged, no update needed.")

# Run the arbitrage checker in a loop
while True:
  try:
    time.sleep(1)
    open_orders_response = get_open_orders()
    if open_orders_response is None:
        print("❌ Error: Could not fetch open orders.")
        time.sleep(5)
        continue  # Skip this iteration
        
    
    # Ensure we have a valid list before processing
    if isinstance(open_orders_response, list):
        open_orders = {order["orderId"]: order["price"] for order in open_orders_response}
    else:
        print(f"Unexpected response from get_open_orders(): {open_orders_response}")
        open_orders = {}   
        time.sleep(5)
        continue  # Skip this iteration
    # Check Buy Orders
    for order_id, buy_price in list(BuyOrders.items()):
        if order_id not in open_orders and open_orders != {}:  # Order was executed
            new_sell_price = round(buy_price + last_spacing, 2)  # Place sell order above
            response = place_mexc_order("SELL", str(new_sell_price), str(ORDER_SIZE / new_sell_price))
            if response and "orderId" in response:
                SellOrders[response["orderId"]] = new_sell_price
                print(f"✅ Sell order placed at {new_sell_price} after buy at {buy_price}")
            else:
                print(f"Failed to place sell order at {new_sell_price}")
            del BuyOrders[order_id]  # Remove executed order from tracking
            

    # Check Sell Orders
        open_orders_response = get_open_orders()
    if open_orders_response is None:
        print("❌ Error: Could not fetch open orders.")
        time.sleep(5)
        continue  # Skip this iteration
        
    
    # Ensure we have a valid list before processing
    if isinstance(open_orders_response, list):
        open_orders = {order["orderId"]: order["price"] for order in open_orders_response}
    else:
        print(f"Unexpected response from get_open_orders(): {open_orders_response}")
        open_orders = {}
        time.sleep(5)
        continue  # Skip this iteration
        
    for order_id, sell_price in list(SellOrders.items()):
        if order_id not in open_orders and open_orders != {}:  # Order was executed
            new_buy_price = round(sell_price - last_spacing ,2)  # Place buy order below
            response = place_mexc_order("BUY", str(new_buy_price), str(ORDER_SIZE / new_buy_price))
            if response  and "orderId" in response:
                BuyOrders[response["orderId"]] = new_buy_price
                print(f"✅ buy order placed at {new_buy_price} after sell at {sell_price}")

            else:
                print(f"Failed to place buy order at {new_buy_price}")
            del SellOrders[order_id]  # Remove executed order from tracking
    currenttime = datetime.datetime.now()
    print(f"📊 Sell: {len(SellOrders)}  Buy: {len(BuyOrders)} Open: {len(open_orders)} time: {currenttime.hour}:{currenttime.minute}")


    #ohlcv = fetch_ohlcv()
    #if ohlcv is None or len(ohlcv) == 0:
     #print("Error: No OHLCV data received, skipping this cycle.")
     #time.sleep(60)  # Wait before retrying
     #continue  # Skip this iteration
    #atr = calculate_atr(ohlcv)
    #atr_avg = np.mean(atr)  # Smoothing ATR

    #dynamic_spacing = adjust_grid_spacing(base_spacing, atr, atr_avg)
    #print(f"New Grid Spacing: {dynamic_spacing:.2f}")
    #update_grid_orders(symbol,dynamic_spacing)       
    time.sleep(10)
  except (requests.exceptions.RequestException, urllib3.exceptions.ProtocolError, urllib3.exceptions.HTTPError) as e:
    logging.error(f"Network error: {e}")
    print(f"🌐 Network error: {e}, retrying in 10 seconds...")
    time.sleep(10)  # Wait before retrying

  except Exception as e:
    logging.error(f"Unexpected error: {e}")
    print(f"⚠️ Unexpected error: {e}, restarting bot...")
    time.sleep(5)  # Shorter wait to restart faster
