# Small-Cap AI Stock Selector

An automated AI agent pipeline designed to screen the U.S. small-cap universe for compelling value and growth opportunities. 

This repository leverages fundamental data screening alongside Google's **Gemini 2.5 Flash** model to not only find stocks with low P/E ratios and high earnings growth, but to actively investigate them for structural value traps.

## 🧠 Architecture

Given the noise and idiosyncratic risks inherent in the small-cap universe, this agent operates in a two-phase workflow:

1. **Phase 1: Quantitative Filter (The Screener)**
   - Scrapes the S&P 600 SmallCap constituents to establish a baseline universe of companies with a history of positive earnings.
   - Evaluates the universe using `yfinance` to filter strictly for companies with a Market Cap between $300M and $2B, a Forward P/E < 15, and Earnings Growth > 20%.
   
2. **Phase 2: Qualitative Investigation (The Analyst)**
   - Passes the quant-screened candidates to the Gemini API.
   - Utilizes a **FastMCP** tool integration to dynamically fetch the latest news and context for each ticker.
   - The LLM synthesizes the fundamental data and news to flag one-time accounting anomalies, cyclical peaks, or macro headwinds, outputting a structured JSON report with a final Conviction Score.

## 📂 Repository Structure

```text
smallcap/
├── agents/
│   ├── __init__.py
│   └── stock_selector.py      # Core Gemini API prompt and reasoning loop
├── mcp_servers/
│   ├── __init__.py
│   └── fundamental_tools.py   # FastMCP server exposing yfinance APIs to the agent
├── data/
│   └── universe.py            # Logic to define the S&P 600 small-cap universe
├── requirements.txt
└── main.py                    # Entry point to execute the pipeline
