import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

VALID_SECTORS = {
    "basic-materials", "communication-services", "consumer-cyclical",
    "consumer-defensive", "energy", "financial-services", "healthcare",
    "industrials", "real-estate", "technology", "utilities",
}

FALLBACK_TECH_TICKERS = [
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "AMZN",
    "META",
    "AVGO",
    "CRM",
    "ORCL",
    "AMD",
    "INTC",
    "CSCO",
    "IBM",
    "QCOM",
    "ADBE",
    "NFLX",
    "SAP",
    "PLTR",
    "UBER",
    "SHOP",
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

    return FALLBACK_TECH_TICKERS


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

    df["pe rank"] = df["trailing pe"].rank()
    df["p/b rank"] = df["p/b data"].rank()
    print(df)
    df.to_excel(f"{choice}_tickers.xlsx", index=False)



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
    while True:
        choice = ask_sector()
        if choice is None:
            print("Bye.")
            break

        if input(f"Confirm '{choice}'? (y/n): ").strip().lower() != "y":
            continue

        main()