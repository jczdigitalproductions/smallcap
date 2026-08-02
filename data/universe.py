import pandas as pd
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def get_small_cap_tickers() -> list[str]:
    """
    Retrieves a universe of US small-cap tickers.
    Scrapes the S&P 600 SmallCap index constituents directly from Wikipedia.
    
    Returns:
        A list of cleaned ticker strings compatible with yfinance.
    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies"
    
    logging.info(f"Fetching small-cap universe from {url}")
    
    try:
        # pandas read_html automatically finds all <table> elements on the page
        tables = pd.read_html(url)
        
        # The constituents table is the first table on this specific Wikipedia page
        df = tables[0]
        
        # Extract the 'Symbol' column and convert to a list
        tickers = df['Symbol'].tolist()
        
        # yfinance uses hyphens for dual-class shares (e.g., 'BF-B' instead of 'BF.B')
        # Wikipedia sometimes uses dots. This normalizes the tickers.
        cleaned_tickers = [str(ticker).replace('.', '-') for ticker in tickers]
        
        logging.info(f"Successfully loaded {len(cleaned_tickers)} small-cap tickers.")
        return cleaned_tickers
        
    except Exception as e:
        logging.error(f"Failed to fetch ticker universe: {e}")
        # Return a small fallback list for testing if the network request fails
        return ["SPSC", "FSS", "LANC", "SXI", "WDFC"]

if __name__ == "__main__":
    # Test the function when running this file directly
    tickers = get_small_cap_tickers()
    print(f"Sample tickers: {tickers[:10]}")
