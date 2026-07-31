import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import yfinance as yf
import plotly.express as px

# ======================
# CONFIG
# ======================
DATA_FILE = "portfolio_data.json"
DEFAULT_ETFS = ["QQQI", "SPYI", "XSPI", "XQQI", "BTCI", "XBCI", "GIAX", "BLOX", "MLPI", "SLJY", "IAUI"]

st.set_page_config(
    page_title="Covered Call ETF Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================
# THEME SETUP
# ======================
if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

def apply_theme():
    if st.session_state.theme == "Dark":
        st.markdown("""
        <style>
        /* Main background */
        .stApp {
            background-color: #0e1117;
            color: #ffffff;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #161b22;
            color: #ffffff;
        }

        /* Titles and headers */
        h1, h2, h3, h4, h5, h6 {
            color: #ffffff !important;
        }

        /* Metrics */
        [data-testid="stMetricValue"] {
            color: #ffffff !important;
        }
        [data-testid="stMetricLabel"] {
            color: #cccccc !important;
        }

        /* Dataframes / tables */
        .stDataFrame {
            background-color: #21262d !important;
        }

        /* Input boxes and cards */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div,
        .stDateInput > div > div > input {
            background-color: #21262d !important;
            color: #ffffff !important;
        }

        /* Buttons */
        .stButton > button {
            background-color: #238636;
            color: white;
            border: none;
        }
        .stButton > button:hover {
            background-color: #2ea043;
            color: white;
        }

        /* General text */
        p, span, label, div {
            color: #e6edf3 !important;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        .stApp {
            background-color: #ffffff;
            color: #000000;
        }
        </style>
        """, unsafe_allow_html=True)

apply_theme()

# ======================
# DATA FUNCTIONS
# ======================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "transactions": [],
        "distributions": [],
        "cash": 0.0,
        "cash_history": [],
        "etfs": DEFAULT_ETFS.copy()
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_current_price(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 2)
    except:
        pass
    return None

def get_last_dividend(ticker):
    try:
        t = yf.Ticker(ticker)
        dividends = t.dividends
        if not dividends.empty:
            last_date = dividends.index[-1].strftime("%Y-%m-%d")
            last_amount = round(float(dividends.iloc[-1]), 4)
            return last_date, last_amount
    except:
        pass
    return None, None

def calculate_position(ticker, data):
    buys = [t for t in data["transactions"] if t["ticker"] == ticker and t["type"] == "BUY"]
    sells = [t for t in data["transactions"] if t["ticker"] == ticker and t["type"] == "SELL"]

    shares_bought = sum(t["shares"] for t in buys)
    shares_sold = sum(t["shares"] for t in sells)
    total_shares = shares_bought - shares_sold

    cost_bought = sum(t["shares"] * t["price"] for t in buys)
    cost_sold = sum(t["shares"] * t["price"] for t in sells)
    total_cost = cost_bought - cost_sold

    roc_total = sum(d.get("roc_amount", 0) for d in data["distributions"] if d["ticker"] == ticker)
    adjusted_cost = max(total_cost - roc_total, 0)
    avg_cost = adjusted_cost / total_shares if total_shares > 0 else 0

    return {
        "shares": round(total_shares, 4),
        "total_cost": round(total_cost, 2),
        "adjusted_cost": round(adjusted_cost, 2),
        "avg_cost": round(avg_cost, 4),
        "roc_total": round(roc_total, 2)
    }

# ======================
# LOAD DATA
# ======================
data = load_data()

# ======================
# SIDEBAR
# ======================
st.sidebar.title("📊 ETF Tracker")

theme_choice = st.sidebar.radio("Theme", ["Dark", "Light"], index=0 if st.session_state.theme == "Dark" else 1)
if theme_choice != st.session_state.theme:
    st.session_state.theme = theme_choice
    st.rerun()

page = st.sidebar.radio(
    "Menu",
    [
        "🏠 Portfolio Overview",
        "➕ Add / Edit Transactions",
        "📥 Enter ROC",
        "🔍 Ticker Details",
        "📅 Dividend Calendar",
        "📈 Charts & Projection",
        "💰 Cash",
        "📰 News",
        "⚙️ Manage ETFs",
        "📄 Reports"
    ]
)

if st.sidebar.button("🔄 Refresh Prices"):
    st.rerun()

# ======================
# PORTFOLIO OVERVIEW
# ======================
if page == "🏠 Portfolio Overview":
    st.title("📊 Portfolio Overview")

    overview_rows = []
    total_market_value = 0
    total_adjusted_cost = 0
    total_income = 0

    for ticker in sorted(data["etfs"]):
        pos = calculate_position(ticker, data)
        price = get_current_price(ticker) or 0

        market_value = pos["shares"] * price
        pnl = market_value - pos["adjusted_cost"]
        pnl_pct = (pnl / pos["adjusted_cost"] * 100) if pos["adjusted_cost"] != 0 else 0

        income = sum(
            d.get("distribution_per_share", 0) * d.get("shares_at_time", 0)
            for d in data["distributions"] if d["ticker"] == ticker
        )

        overview_rows.append({
            "Ticker": ticker,
            "Shares": pos["shares"],
            "Avg Cost": pos["avg_cost"],
            "Price": price,
            "Market Value": round(market_value, 2),
            "Adjusted Cost": pos["adjusted_cost"],
            "P&L $": round(pnl, 2),
            "P&L %": round(pnl_pct, 2),
            "ROC Applied": pos["roc_total"],
            "Income Received": round(income, 2)
        })

        total_market_value += market_value
        total_adjusted_cost += pos["adjusted_cost"]
        total_income += income

    st.dataframe(pd.DataFrame(overview_rows), use_container_width=True)

    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Market Value", f"${total_market_value:,.2f}")
    col2.metric("Total Adjusted Cost", f"${total_adjusted_cost:,.2f}")
    col3.metric("Unrealized P&L", f"${total_market_value - total_adjusted_cost:,.2f}")

    col4, col5 = st.columns(2)
    col4.metric("Total Income Received", f"${total_income:,.2f}")
    col5.metric("Cash", f"${data.get('cash', 0):,.2f}")

# --------------------------
# ADD / EDIT TRANSACTIONS
# --------------------------
elif page == "➕ Add / Edit Transactions":
    st.title("➕ Add / Edit Transactions")

    tab1, tab2 = st.tabs(["Add Transaction", "Delete Transaction"])

    with tab1:
        with st.form("add_transaction"):
            ticker = st.selectbox("ETF", data["etfs"])
            trans_type = st.selectbox("Type", ["BUY", "SELL"])
            shares = st.number_input("Shares", min_value=0.01, step=1.0, format="%.2f")
            price = st.number_input("Price per Share", min_value=0.01, step=0.01, format="%.2f")
            date = st.date_input("Date", value=datetime.today())
            notes = st.text_input("Notes (optional)")

            if st.form_submit_button("Save Transaction"):
                data["transactions"].append({
                    "id": len(data["transactions"]) + 1,
                    "ticker": ticker,
                    "type": trans_type,
                    "shares": float(shares),
                    "price": float(price),
                    "date": str(date),
                    "notes": notes
                })
                save_data(data)
                st.success(f"✅ {trans_type} saved")
                st.rerun()

    with tab2:
        if data["transactions"]:
            st.dataframe(pd.DataFrame(data["transactions"]), use_container_width=True)
            delete_id = st.number_input("Transaction ID to delete", min_value=1, step=1)
            if st.button("Delete Transaction"):
                data["transactions"] = [t for t in data["transactions"] if t.get("id") != delete_id]
                for i, t in enumerate(data["transactions"], 1):
                    t["id"] = i
                save_data(data)
                st.success("Deleted")
                st.rerun()
        else:
            st.info("No transactions yet.")

# --------------------------
# ENTER ROC
# --------------------------
elif page == "📥 Enter ROC":
    st.title("📥 Enter Distribution & ROC")

    st.markdown("### Automatic Last Dividend Helper")
    helper_ticker = st.selectbox("Check last dividend for:", data["etfs"], key="helper")

    if "last_div_amount" not in st.session_state:
        st.session_state.last_div_amount = None
        st.session_state.last_div_date = None
        st.session_state.last_div_ticker = None

    if st.button("Get Last Dividend from Yahoo"):
        last_date, last_amount = get_last_dividend(helper_ticker)
        if last_amount:
            st.session_state.last_div_amount = last_amount
            st.session_state.last_div_date = last_date
            st.session_state.last_div_ticker = helper_ticker
            st.success(f"Last dividend for **{helper_ticker}**: **${last_amount}** on {last_date}")
        else:
            st.warning("Could not find recent dividend data.")

    if st.session_state.last_div_amount is not None:
        st.info(f"Ready: **{st.session_state.last_div_ticker}** → ${st.session_state.last_div_amount} ({st.session_state.last_div_date})")
        if st.button("✅ Use this dividend amount"):
            st.session_state.fill_dist = st.session_state.last_div_amount
            st.session_state.fill_ticker = st.session_state.last_div_ticker
            st.success("Dividend amount ready for the form below.")

    st.divider()
    st.markdown("### Enter Distribution + ROC")

    default_ticker = st.session_state.get("fill_ticker", data["etfs"][0])
    default_dist = st.session_state.get("fill_dist", 0.0)

    with st.form("distribution_form"):
        ticker_index = data["etfs"].index(default_ticker) if default_ticker in data["etfs"] else 0
        ticker = st.selectbox("Select ETF", data["etfs"], index=ticker_index)
        dist_per_share = st.number_input("Distribution per Share ($)", min_value=0.0, value=float(default_dist), format="%.4f")
        roc_pct = st.number_input("ROC Percentage (%)", min_value=0.0, max_value=100.0, value=100.0, step=1.0, format="%.0f")
        dist_date = st.date_input("Date", value=datetime.today())

        if st.form_submit_button("Save Distribution"):
            pos = calculate_position(ticker, data)
            shares = pos["shares"]

            roc_dollar = dist_per_share * (roc_pct / 100.0) * shares
            ordinary_dollar = dist_per_share * ((100 - roc_pct) / 100.0) * shares

            data["distributions"].append({
                "ticker": ticker,
                "date": str(dist_date),
                "distribution_per_share": dist_per_share,
                "roc_percent": roc_pct,
                "roc_amount": round(roc_dollar, 2),
                "ordinary_amount": round(ordinary_dollar, 2),
                "shares_at_time": shares
            })
            save_data(data)
            st.success(f"✅ Saved | ROC: {roc_pct:.0f}% | Reduction: ${roc_dollar:,.2f}")
            st.session_state.fill_dist = 0.0
            st.session_state.fill_ticker = None
            st.rerun()

# --------------------------
# TICKER DETAILS
# --------------------------
elif page == "🔍 Ticker Details":
    st.title("🔍 Ticker Details")

    selected = st.selectbox("Choose ETF", data["etfs"])
    pos = calculate_position(selected, data)
    current_price = get_current_price(selected)

    st.subheader(selected)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Shares", f"{pos['shares']:.2f}")
    c2.metric("Avg Cost", f"${pos['avg_cost']:.4f}")
    c3.metric("Price", f"${current_price:.2f}" if current_price else "—")
    c4.metric("Value", f"${(pos['shares'] * current_price):,.2f}" if current_price else "—")

    st.markdown("#### Transactions")
    txs = [t for t in data["transactions"] if t["ticker"] == selected]
    st.dataframe(pd.DataFrame(txs) if txs else pd.DataFrame(), use_container_width=True)

    st.markdown("#### Distributions")
    dists = [d for d in data["distributions"] if d["ticker"] == selected]
    st.dataframe(pd.DataFrame(dists) if dists else pd.DataFrame(), use_container_width=True)

# --------------------------
# DIVIDEND CALENDAR
# --------------------------
elif page == "📅 Dividend Calendar":
    st.title("📅 Dividend Calendar")

    if data["distributions"]:
        dist_df = pd.DataFrame(data["distributions"])
        dist_df["date"] = pd.to_datetime(dist_df["date"])
        dist_df = dist_df.sort_values("date", ascending=False)
        st.dataframe(dist_df, use_container_width=True)
    else:
        st.info("No distributions recorded yet.")

# --------------------------
# CHARTS & PROJECTION
# --------------------------
elif page == "📈 Charts & Projection":
    st.title("📈 Charts & Income Projection")

    st.subheader("Estimated Future Income")

    projection_data = []
    for ticker in data["etfs"]:
        pos = calculate_position(ticker, data)
        if pos["shares"] <= 0:
            continue

        ticker_dists = [d for d in data["distributions"] if d["ticker"] == ticker]
        if ticker_dists:
            latest = sorted(ticker_dists, key=lambda x: x["date"], reverse=True)[0]
            monthly = latest["distribution_per_share"] * pos["shares"]
            weekly = monthly / 4.33
            yearly = monthly * 12
        else:
            monthly = weekly = yearly = 0

        projection_data.append({
            "Ticker": ticker,
            "Shares": pos["shares"],
            "Weekly": round(weekly, 2),
            "Monthly": round(monthly, 2),
            "Yearly": round(yearly, 2)
        })

    if projection_data:
        proj_df = pd.DataFrame(projection_data)
        st.dataframe(proj_df, use_container_width=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Weekly", f"${proj_df['Weekly'].sum():,.2f}")
        c2.metric("Total Monthly", f"${proj_df['Monthly'].sum():,.2f}")
        c3.metric("Total Yearly", f"${proj_df['Yearly'].sum():,.2f}")
    else:
        st.info("No data to project yet.")

    st.divider()
    st.subheader("Portfolio Allocation")

    alloc_data = []
    for ticker in data["etfs"]:
        pos = calculate_position(ticker, data)
        price = get_current_price(ticker) or 0
        value = pos["shares"] * price
        if value > 0:
            alloc_data.append({"Ticker": ticker, "Value": value})

    if alloc_data:
        fig = px.pie(pd.DataFrame(alloc_data), values="Value", names="Ticker", title="Allocation")
        st.plotly_chart(fig, use_container_width=True)

# --------------------------
# CASH
# --------------------------
elif page == "💰 Cash":
    st.title("💰 Cash Management")

    st.metric("Current Cash Balance", f"${data.get('cash', 0):,.2f}")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Add Cash")
        add_amount = st.number_input("Amount to Add", min_value=0.0, step=50.0, key="add_cash")
        if st.button("Add Cash"):
            data["cash"] = data.get("cash", 0) + add_amount
            data.setdefault("cash_history", []).append({
                "date": str(datetime.today().date()),
                "type": "ADD",
                "amount": add_amount
            })
            save_data(data)
            st.success(f"Added ${add_amount:,.2f}")
            st.rerun()

    with col2:
        st.subheader("Remove Cash")
        remove_amount = st.number_input("Amount to Remove", min_value=0.0, step=50.0, key="remove_cash")
        if st.button("Remove Cash"):
            data["cash"] = max(0, data.get("cash", 0) - remove_amount)
            data.setdefault("cash_history", []).append({
                "date": str(datetime.today().date()),
                "type": "REMOVE",
                "amount": remove_amount
            })
            save_data(data)
            st.success(f"Removed ${remove_amount:,.2f}")
            st.rerun()

# --------------------------
# NEWS
# --------------------------
elif page == "📰 News":
    st.title("📰 ETF News")

    selected_news = st.selectbox("Select ETF", data["etfs"])

    try:
        ticker_obj = yf.Ticker(selected_news)
        news = ticker_obj.news
        if news:
            for item in news[:6]:
                st.markdown(f"**{item.get('title', 'No title')}**")
                if item.get("link"):
                    st.markdown(f"[Read more]({item['link']})")
                st.markdown("---")
        else:
            st.info("No recent news found.")
    except:
        st.warning("Could not load news.")

# --------------------------
# MANAGE ETFs
# --------------------------
elif page == "⚙️ Manage ETFs":
    st.title("⚙️ Manage ETFs")

    st.write("Currently tracked:")
    st.write(", ".join(data["etfs"]))

    new_ticker = st.text_input("Add new ETF").upper().strip()
    if st.button("Add ETF"):
        if new_ticker and new_ticker not in data["etfs"]:
            data["etfs"].append(new_ticker)
            save_data(data)
            st.success(f"Added {new_ticker}")
            st.rerun()

# --------------------------
# REPORTS
# --------------------------
elif page == "📄 Reports":
    st.title("📄 Reports")

    if st.button("Generate Report"):
        report_rows = []
        for t in data["etfs"]:
            p = calculate_position(t, data)
            if p["shares"] <= 0:
                continue
            report_rows.append({
                "ETF": t,
                "Shares": p["shares"],
                "Avg Cost": p["avg_cost"],
                "Adjusted Cost": p["adjusted_cost"],
                "ROC Received": p["roc_total"]
            })

        if report_rows:
            rdf = pd.DataFrame(report_rows)
            st.dataframe(rdf, use_container_width=True)
            csv = rdf.to_csv(index=False).encode()
            st.download_button(
                "Download CSV",
                csv,
                f"etf_report_{datetime.today().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
        else:
            st.warning("No positions found.")