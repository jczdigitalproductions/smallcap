import concurrent.futures
import yfinance as yf
from fastmcp import FastMCP

# Initialize the FastMCP server
# We disable strict input validation to allow the LLM flexibility in passing lists
mcp = FastMCP(name="SmallCapScreener")

@mcp.tool
def screen_universe(
    tickers: list[str], 
    max_pe: float = 15.0, 
    min_earnings_growth: float = 0.20
) -> list[dict]:
    """
    Screens a list of stock tickers for small-cap value/growth criteria.
    
    Filters applied:
    1. Market Cap: Between $300M and $2B (Small-Cap universe)
    2. Forward P/E Ratio: Less than max_pe
    3. Earnings Growth: Greater than min_earnings_growth (e.g., 0.20 for 20%)
    
    Args:
        tickers: A list of stock ticker symbols (e.g., ["IWM", "FSLR"]).
        max_pe: The maximum acceptable Forward P/E ratio.
        min_earnings_growth: The minimum acceptable earnings growth rate.
        
    Returns:
        A list of dictionaries containing the financial metrics of the stocks that passed the screen.
    """
    passed_screen = []
    
    def evaluate_ticker(ticker_symbol: str):
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            
            # Extract fundamental metrics from Yahoo Finance
            market_cap = info.get("marketCap", 0)
            forward_pe = info.get("forwardPE")
            earnings_growth = info.get("earningsGrowth")
            
            # 1. Market Cap Filter: strictly $300M to $2B
            if not (300_000_000 <= market_cap <= 2_000_000_000):
                return None
                
            # 2. Valuation Filter: Forward P/E must exist and be below the threshold
            if forward_pe is None or forward_pe > max_pe:
                return None
                
            # 3. Growth Filter: Earnings growth must exist and be above the threshold
            if earnings_growth is None or earnings_growth < min_earnings_growth:
                return None
                
            # If all criteria are met, return the structured data for the LLM
            return {
                "ticker": ticker_symbol,
                "market_cap": market_cap,
                "forward_pe": forward_pe,
                "earnings_growth": earnings_growth,
                "profit_margins": info.get("profitMargins"),
                "industry": info.get("industry", "Unknown"),
                "sector": info.get("sector", "Unknown"),
                "company_name": info.get("shortName", ticker_symbol)
            }
            
        except Exception as e:
            # Silently catch exceptions (e.g., delisted tickers, missing data) to prevent the batch from failing
            return None

    # Execute the fetches concurrently to avoid long latency timeouts in the LLM
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(evaluate_ticker, t): t for t in tickers}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                passed_screen.append(result)
                
    return passed_screen

@mcp.tool
def get_company_news(ticker: str) -> list[dict]:
    """
    Fetches the latest news headlines for a specific ticker to check for macro headwinds.
    
    Args:
        ticker: The stock ticker symbol.
    """
    try:
        stock = yf.Ticker(ticker)
        news_items = stock.news
        
        # Format the news down to the essentials to save context window space
        formatted_news = []
        for item in news_items[:5]:  # Limit to 5 most recent articles
            formatted_news.append({
                "title": item.get("title"),
                "publisher": item.get("publisher"),
                "link": item.get("link")
            })
        return formatted_news
    except Exception:
        return [{"error": f"Could not retrieve news for {ticker}"}]


if __name__ == "__main__":
    # Start the FastMCP server via standard I/O (default for MCP clients)
    mcp.run()
