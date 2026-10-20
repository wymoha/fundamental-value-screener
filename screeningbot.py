import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
import time
import subprocess
import os
VALID_SECTORS = {
    "basic-materials", "communication-services", "consumer-cyclical",
    "consumer-defensive", "energy", "financial-services", "healthcare",
    "industrials", "real-estate", "technology", "utilities",
}

FALLBACK_TICKERS = [
    "NVDA", "MSFT", "AAPL", "GOOGL", "AMZN", "META", "AVGO", "TSLA", "BRK-B", "LLY",
    "JPM", "WMT", "V", "ORCL", "MA", "XOM", "NFLX", "COST", "JNJ", "HD",
    "PLTR", "PG", "BAC", "ABBV", "CVX", "KO", "AMD", "GE", "CSCO", "TMUS",
    "WFC", "MS", "CRM", "PM", "IBM", "ABT", "AXP", "LIN", "MCD", "GS",
    "MRK", "DIS", "T", "UBER", "RTX", "PEP", "CAT", "NOW", "INTU", "VZ",
]



def get_tickers(sector):
    try:
        tech = yf.Sector(sector)
        top_companies = getattr(tech, "top_companies", None)
        if top_companies is not None and hasattr(top_companies, "index"):
            tickers = top_companies.index.tolist()
            if tickers:
                return tickers
    except Exception as exc:
        print(f"Yahoo Finance sector lookup failed for technology: {exc}")
        print("Using fallback list of major tech tickers.")
    except Exception as e:
        msg = str(e)
        if '404' in msg or "Not Found" in msg:
            print(f"{choice}: not found (check the symbol/suffix, or no data for this endpoint)")
            return None
        raise

    return FALLBACK_TICKERS


def fetch_ticker_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        pe_data = info.get("trailingPE")
        financials = stock.financials
        if financials.empty:
            return None

        net_income = financials.loc[financials.index == "Net Income"]
        revenue = financials.loc[financials.index == "Total Revenue"]
        if net_income.empty or revenue.empty:
            return None

        net_income_thisyear = net_income.iloc[:, 0].iloc[0]
        net_income_lastyear = net_income.iloc[:, 1].iloc[0]
        growing = net_income_lastyear < net_income_thisyear
        revenue_current = revenue.iloc[:, 0].iloc[0]
        if revenue_current == 0:
            return None

        profit_margin = net_income_thisyear / revenue_current

        bookvalue_pershare = info.get("bookValue")
        marketprice = info.get("regularMarketPrice")
        p_b = marketprice / bookvalue_pershare
        if marketprice is None or bookvalue_pershare in (None, 0):
            p_b = None


        return {
            "ticker": ticker,
            "p/b data": p_b,
            "trailing pe": pe_data,
            "profit margin": profit_margin,
            "growing": growing,
        }
    except Exception:
        return None


def main():
    company_list = get_tickers(choice)
    data = []

    with ThreadPoolExecutor(max_workers=10) as execute:
        results = list(execute.map(fetch_ticker_data, company_list))
        for result in results:
            if result is not None:
                data.append(result)

    df = pd.DataFrame(data)

    if df.empty:
        print("No valid tickers returned from the provider.")
        return
    df['pe rank'] = df['trailing pe'].rank()
    df['p/b rank'] = df['p/b data'].rank()    
    by_pb = df.sort_values(by='p/b rank', ignore_index=True).drop(columns='pe rank')
    by_pe = df.sort_values(by='pe rank', ignore_index=True).drop(columns='p/b rank')
    combined = df[(df['pe rank'] <= 50) & (df['p/b rank'] <= 50)]
    try:
        with pd.ExcelWriter(path=userpath) as writer:
            by_pb.to_excel(writer, sheet_name="by p-b", index=False)
            by_pe.to_excel(writer, sheet_name="by p-e", index=False)
            combined.to_excel(writer, sheet_name="combined top 50",index=False)
    except Exception as e:
        backuppath = os.path.join(os.getcwd(),'financialdata.xlsx')
        with pd.ExcelWriter(path=backuppath) as writer:
                    by_pb.to_excel(writer, sheet_name="by p-b", index=False)
                    by_pe.to_excel(writer, sheet_name="by p-e", index=False)
                    combined.to_excel(writer, sheet_name="combined top 50",index=False)
        
    print(df)
   



SECTOR_LIST = sorted(VALID_SECTORS)
AZERTY_DIGITS = str.maketrans("&é\"'(§è!çà", "1234567890")


def ask_sector():
    print("\nSectors")
    for i, name in enumerate(SECTOR_LIST, 1):
        print(f"  {i:>2}. {name}")
    print("Type a number or a name. Leave empty to quit.")

    while True:
        raw = input("Choose a sector: ").strip().lower()
        if raw == "":
            return None

        raw = raw.translate(AZERTY_DIGITS)
        if raw.isdigit() and 1 <= int(raw) <= len(SECTOR_LIST):
            return SECTOR_LIST[int(raw) - 1]

        raw = raw.replace(" ", "-")
        if raw in VALID_SECTORS:
            return raw

        print(f"'{raw}' is not a valid sector, try again.")


if __name__ == "__main__":
    subprocess.run(["cls" if os.name == "nt" else "clear"])

    print("Please input the full path to the folder.")
    time.sleep(1)
    print("DO NOT ENTER A RELATIVE PATH.")
    userfolder = input("PATH: ")

    while True:
        choice = ask_sector()
        if choice is None:
            print("Bye.")
            break

        if input(f"Confirm '{choice}'? (y/n): ").strip().lower() != "y":
            continue

        userpath = os.path.join(userfolder, f"{choice}-financialdata.xlsx")
        print(f"PATH={userpath}")
        time.sleep(1)

        main()