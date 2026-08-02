import os
import json
import logging
from google import genai
from google.genai import types
from fastmcp import FastMCP

# Import the universe function you built earlier
from data.universe import get_small_cap_tickers

# Configure logging to track the agent's progress
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def run_agent():
    """
    Main orchestration loop for the small-cap screening agent.
    """
    # 1. Ensure API key is set
    # Get your key from Google AI Studio and set it in your environment
    if "GEMINI_API_KEY" not in os.environ:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    
    # 2. Initialize the Gemini Client
    # We use the new google-genai SDK
    client = genai.Client()
    
    # We use gemini-2.5-flash for speed and cost-effectiveness in multi-tool workflows
    MODEL_ID = 'gemini-2.5-flash'
    
    # 3. Connect to the FastMCP Server
    logging.info("Connecting to FastMCP fundamental tools...")
    # This assumes fundamental_tools.py is running locally or we import the tools directly.
    # For a direct Python integration without spinning up a separate server process, 
    # we can import the MCP object directly if they are in the same python environment.
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mcp_servers.fundamental_tools import mcp
    
    # 4. Get the universe of tickers
    logging.info("Fetching S&P 600 SmallCap universe...")
    universe = get_small_cap_tickers()
    
    if not universe:
        logging.error("Universe is empty. Aborting.")
        return
        
    logging.info(f"Loaded {len(universe)} tickers. Starting Phase 1 Quantitative Screen...")
    
    # 5. Phase 1: Quantitative Screen
    # We call the Python function directly here rather than using the LLM 
    # to save tokens and guarantee execution on the full list.
    # We chunk the universe to avoid hitting yfinance rate limits all at once.
    chunk_size = 50
    passed_candidates = []
    
    from mcp_servers.fundamental_tools import screen_universe, get_company_news
    
    for i in range(0, min(200, len(universe)), chunk_size): # Limit to first 200 for testing
        chunk = universe[i:i + chunk_size]
        logging.info(f"Screening batch {i//chunk_size + 1}...")
        results = screen_universe(chunk, max_pe=15.0, min_earnings_growth=0.20)
        passed_candidates.extend(results)
        
    logging.info(f"Phase 1 Complete: {len(passed_candidates)} candidates passed the quantitative screen.")
    
    if not passed_candidates:
        logging.info("No candidates met the criteria today.")
        return

    # 6. Phase 2: Qualitative Investigation via Gemini API
    # We define the system instruction instructing the model on how to evaluate the data
    system_instruction = """
    You are a specialized equity analyst focusing on US small-cap stocks. 
    Your objective is to review the provided fundamental data and recent news context for companies that have screened for low P/E (<15) and high earnings growth (>20%).

    Determine if the metrics are genuine or a value trap. Specifically, look for and flag:
    1. One-time asset sales or tax benefits artificially inflating earnings growth.
    2. Cyclical peaks where the market is pricing in a future earnings collapse (explaining the low P/E).
    3. Heavy reliance on a single customer or impending regulatory risks.

    Output your analysis in a structured JSON format matching this schema:
    {
      "ticker": "string",
      "conviction_score": integer (1-10),
      "risk_narrative": "string (1-2 paragraphs detailing the risks)",
      "growth_thesis": "string (1 paragraph explaining why the growth might be sustainable)"
    }
    """
    
    logging.info("Starting Phase 2: Qualitative Analysis via Gemini...")
    
    final_reports = []
    
    # Analyze each candidate
    for candidate in passed_candidates:
        ticker = candidate['ticker']
        logging.info(f"Analyzing {ticker}...")
        
        # We pass the get_company_news tool to the model so it can investigate
        # The new SDK handles function calling automatically if we provide the python function
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[get_company_news],
            temperature=0.2, # Low temperature for more analytical responses
            response_mime_type="application/json", # Force JSON output
        )
        
        # Construct the prompt with the fundamental data we already gathered
        prompt = f"""
        Please analyze the following small-cap candidate:
        
        Fundamental Data:
        {json.dumps(candidate, indent=2)}
        
        Use your tools to fetch recent news for {ticker} to assess the macro and company-specific context.
        """
        
        try:
            # We use generate_content. The SDK automatically detects the need to call the tool,
            # executes the get_company_news python function, and feeds the result back to the model
            # to generate the final JSON response.
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
                config=config
            )
            
            # Parse the JSON response
            try:
                analysis = json.loads(response.text)
                final_reports.append(analysis)
                logging.info(f"Finished analyzing {ticker}. Score: {analysis.get('conviction_score')}")
            except json.JSONDecodeError:
                logging.error(f"Failed to parse JSON for {ticker}: {response.text}")
                
        except Exception as e:
             logging.error(f"API Error analyzing {ticker}: {e}")

    # 7. Output Final Results
    logging.info("=== FINAL ANALYSIS COMPLETE ===")
    
    # Sort by highest conviction score
    final_reports.sort(key=lambda x: x.get('conviction_score', 0), reverse=True)
    
    print("\n--- TOP CANDIDATES ---")
    for report in final_reports[:5]: # Print top 5
        print(f"\nTicker: {report.get('ticker')}")
        print(f"Conviction: {report.get('conviction_score')}/10")
        print(f"Thesis: {report.get('growth_thesis')}")
        print(f"Risks: {report.get('risk_narrative')}")
        print("-" * 30)

if __name__ == "__main__":
    run_agent()
