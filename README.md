📌 Overview
This is a Python-based Grid Trading Bot designed for cryptocurrency markets.
It places buy and sell orders at predefined intervals (“grid levels”) and automatically rebalances when an order is filled.
Grid trading works best in sideways or slightly volatile markets, capturing small price movements for profit.

🚀 Features
Fully automated grid placement & tracking.

Dynamic order replacement when a trade is executed.

Works with CEX exchanges (customizable API integration).

Adjustable grid size, range, and investment amount.

Logs all executed trades for tracking performance.

🛠 Requirements
Before running the bot, make sure you have:

Python 3.9+

API keys from your exchange (with trading permissions enabled).

Installed dependencies from requirements.txt:

bash
Copy code
pip install -r requirements.txt
📂 Project Structure
bash
Copy code
grid_bot/
│── GridBot.py          # Main bot functions
│── requirements.txt     # Python dependencies
│── README.md            # Documentation
⚙️ Setup & Usage
Clone the repository:

bash
Copy code
git clone https://github.com/username/GridBot.git
cd grid-bot
Install dependencies:

bash
Copy code
pip install -r requirements.txt
Add your API keys in config.py.

Configure:

Base and quote currency (e.g., BTC/USDT)

Grid size (number of price levels)

Grid range (min & max price)

Order size per grid level

Run the bot:

bash
Copy code
python grid_bot.py
📊 Example
Pair: BTC/USDT

Range: $28,000 - $32,000

Grid size: 10 levels

Order size: 0.001 BTC

The bot will:

Place buy orders at intervals below market price.

Place sell orders at intervals above market price.

Reposition orders when filled to maintain the grid.

⚠️ Disclaimer
This software is provided for educational purposes only.
Trading cryptocurrencies involves high risk.
The author is not responsible for financial losses resulting from using this bot.
