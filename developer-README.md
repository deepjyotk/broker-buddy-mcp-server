




### Buy a share
1. can you buy 1 shares of 3IINFOLTD?



## Shares suffixes
| Suffix / Series | Meaning                                      | Trading Rules                                               |
| --------------- | -------------------------------------------- | ----------------------------------------------------------- |
| **EQ**          | Equity                                       | Normal trading – both intraday & delivery allowed           |
| **BE**          | Book Entry / Trade-to-Trade                  | Only delivery allowed (no intraday); often for surveillance |
| **BL**          | Block Deals                                  | Special window for block deals between institutions         |
| **BT**          | Buy Today                                    | Allows same-day buy & delivery settlement                   |
| **GC**          | Government Securities                        | Debt instruments                                            |
| **IQ**          | Qualified Institutional Buyers (QIB) segment | Only QIBs can trade                                         |
| **RL**          | Rolling Settlement – Limited                 | Special category, restricted trading                        |



🔹 Buy Queries (examples users might give)

"Buy 50 shares of TCS at market price."
→ Direct market buy, quantity + ticker specified.

"Place a limit order to buy Reliance at ₹2,500."
→ Limit buy, user specifies target price.

"Invest ₹10,000 into Infosys at the best available price."
→ Fund-based order, not quantity-based.

"Buy HDFC Bank shares if the price drops below ₹1,600 today."
→ Conditional trigger order.

"Accumulate 5 shares of ITC every week for the next month."
→ Recurring / systematic buy order.



🔹 Sell Queries (examples users might give)

"Sell 1 shares of 3IINFOLTD at market price."
→ Straightforward market sell.

"Place a stop-loss order to sell Reliance if it falls below ₹2,400."
→ Risk management sell order.

"Book profits by selling TCS when it reaches ₹4,200."
→ Profit-taking limit sell.

"Sell half of my holdings in HDFC Bank now."
→ Partial position exit.

"Exit all positions in ITC today before market close."
→ Complete liquidation with a time condition.




# crypto:
Great question — designing a **Coinbase trading MCP server** means you need to anticipate what kinds of natural user queries your agents/tools should support. Since you’re new to crypto, let’s break it down into categories of queries that a typical user might ask.

---

## 1. **Account & Portfolio Queries**

Users will want to check their account state and holdings:

* “What’s my current portfolio balance?”
* “Show me all my crypto holdings.”
* “How much Bitcoin do I have?”
* “What’s the value of my Ethereum in USD right now?”
* “Did I receive any USDC from yesterday’s transaction?”

---

## 2. **Market Data Queries**

These are about real-time prices, trends, or coin information:

* “What’s the current price of Bitcoin?”
* “Show me the last 24h price change for Solana.”
* “Which coins are trending right now?”
* “What’s the historical price of Ethereum for the past 7 days?”
* “What are the top gainers today on Coinbase?”

---

## 3. **Trade Execution Queries**

Placing buy/sell orders is the core functionality:

* “Buy \$100 worth of Bitcoin.”
* “Place a limit order to buy 0.5 ETH at \$2,500.”
* “Sell 0.01 BTC at market price.”
* “Cancel my open order for ADA.”
* “Show me my open orders.”

---

## 4. **Funding & Transactions**

Crypto involves deposits, withdrawals, and transfers:

* “Deposit \$50 from my bank to Coinbase.”
* “Withdraw 0.1 ETH to this wallet address.”
* “Show me my last 5 transactions.”
* “What are the fees for sending USDC to another wallet?”

---

## 5. **General Queries for Beginners**

Since you mentioned you’re new to crypto, many users will also be:

* “What is a limit order vs market order?”
* “Explain staking rewards on Coinbase.”
* “What’s the minimum amount I can invest in Bitcoin?”
* “Is trading free on Coinbase or are there fees?”

---

## 6. **Advanced Queries (Power Users)**

If you want your MCP server to be future-proof:

* “Stream live prices for BTC and ETH.”
* “Show me my realized and unrealized P\&L (profit & loss).”
* “Give me the order book for SOL/USDT.”
* “What’s my average buy price of BTC?”
* “Set an alert if ETH goes above \$3,000.”

---

✅ A good starting point for your **MCP server** would be:

* `get_portfolio`
* `get_balance` (for a specific coin)
* `get_market_price` (with history option)
* `place_order` (market, limit, stop)
* `cancel_order`
* `list_orders` (open, filled, canceled)
* `deposit`, `withdraw`
* `transaction_history`

---

Would you like me to **map these user queries into concrete MCP tool definitions** (like input/output schemas for `place_order`, `get_market_price`, etc.), so you can directly design your Coinbase trading server?
