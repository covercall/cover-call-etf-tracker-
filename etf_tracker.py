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
# THEME
# ======================
if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

def apply_theme():
    if st.session_state.theme == "Dark":
        st.markdown("""
        <style>
        .stApp {
            background-color: #0e1117;
            color: #ffffff;
        }
        section[data-testid="stSidebar"] {
            background-color: #161b22;
            color: #ffffff;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #ffffff !important;
        }
        [data-testid="stMetricValue"] {
            color: #ffffff !important;
        }
        [data-testid="stMetricLabel"] {
            color: #cccccc !important;
        }
        /* Dropdowns and inputs - dark background with white text */
        .stSelectbox div[data-baseweb="select"] > div {
            background-color: #21262d !important;
            color: #ffffff !important;
        }
        .stSelectbox div[data-baseweb="select"] span {
            color: #ffffff !important;
        }
        div[data-baseweb="popover"] {
            background-color: #21262d !important;
        }
        div[data-baseweb="popover"] li {
            color: #ffffff !important;
            background-color: #21262d !important;
        }
        div[data-baseweb="popover"] li:hover {
            background-color: #30363d !important;
        }
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stDateInput > div > div > input {
            background-color: #21262d !important;
            color: #ffffff !important;
        }
        .stButton > button {
            background-color: #238636;
            color: white;
            border: none;
        }
        .stButton > button:hover {
            background-color: #2ea043;
            color: white;
        }
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
            color: #1f2328;
        }
        .stSelectbox div[data-baseweb="select"] > div {
            background-color: #ffffff !important;
            color: #1f2328 !important;
        }
        .stSelectbox div[data-baseweb="select"] span {
            color: #1f2328 !important;
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
            return round(float(hist["Close"].iloc[-1]), 4)
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
        "➕ Add / Edit Positions",
        "📥 Enter / Edit ROC",
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
    total_market_value = 0.0
    total_adjusted_cost = 0.0
    total_income = 0.0

    for ticker in sorted(data["etfs"]):
        pos = calculate_position(ticker, data)
        price = get_current_price(ticker) or 0.0

        market_value = pos["shares"] * price
        pnl = market_value - pos["adjusted_cost"]
        pnl_pct = (pnl / pos["adjusted_cost"] * 100) if pos["adjusted_cost"] != 0 else 0.0

        income = sum(
            d.get("distribution_per_share", 0) * d.get("shares_at_time", 0)
            for d in data["distributions"] if d["ticker"] == ticker
        )

        overview_rows.append({
            "Ticker": ticker,
            "Shares": f"{pos['shares']:.4f}",
            "Avg Cost": f"{pos['avg_cost']:.4f}",
            "Price": f"{price:.4f}" if price else "—",
            "Market Value": round(market_value, 2),
            "Adjusted Cost": pos["adjusted_cost"],
            "P&L $": round(pnl, 2),
            "P&L %": f"{pnl_pct:.2f}%",
            "ROC Applied": pos["roc_total"],
            "Income Received": round(income, 2)
        })

        total_market_value += market_value
        total_adjusted_cost += pos["adjusted_cost"]
        total_income += income

    df = pd.DataFrame(overview_rows)

    def style_pnl(row):
        styles = [""] * len(row)
        try:
            pnl_val = float(str(row["P&L $"]).replace(",", ""))
            if pnl_val > 0:
                styles[df.columns.get_loc("P&L $")] = "color: #3fb950; font-weight: bold"
                styles[df.columns.get_loc("P&L %")] = "color: #3fb950; font-weight: bold"
            elif pnl_val < 0:
                styles[df.columns.get_loc("P&L $")] = "color: #f85149; font-weight: bold"
                styles[df.columns.get_loc("P&L %")] = "color: #f85149; font-weight: bold"
        except:
            pass
        return styles

    if not df.empty:
        st.dataframe(df.style.apply(style_pnl, axis=1), use_container_width=True)
    else:
        st.info("No positions yet.")

    # ===== SUMMARY METRICS =====
    st.divider()
    st.subheader("Portfolio Summary")

    total_pnl = total_market_value - total_adjusted_cost
    total_pnl_pct = (total_pnl / total_adjusted_cost * 100) if total_adjusted_cost != 0 else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Market Value", f"${total_market_value:,.2f}")
    col2.metric("Adjusted Cost (after ROC)", f"${total_adjusted_cost:,.2f}")
    col3.metric("Unrealized P&L $", f"${total_pnl:,.2f}")

    col4, col5, col6 = st.columns(3)

    # Color the total P&L %
    pnl_pct_label = f"{total_pnl_pct:+.2f}%"
    if total_pnl > 0:
        col4.markdown(f"**Total P&L %**  \n<span style='color:#3fb950; font-size:1.6rem; font-weight:bold;'>{pnl_pct_label}</span>", unsafe_allow_html=True)
    elif total_pnl < 0:
        col4.markdown(f"**Total P&L %**  \n<span style='color:#f85149; font-size:1.6rem; font-weight:bold;'>{pnl_pct_label}</span>", unsafe_allow_html=True)
    else:
        col4.metric("Total P&L %", f"{total_pnl_pct:.2f}%")

    col5.metric("Total Income Received", f"${total_income:,.2f}")
    col6.metric("Cash", f"${data.get('cash', 0):,.2f}")

# --------------------------
# ADD / EDIT POSITIONS
# --------------------------
elif page == "➕ Add / Edit Positions":
    st.title("➕ Add / Edit Positions")

    tab1, tab2, tab3 = st.tabs(["Add Position", "Sell Position", "Delete Transaction"])

    with tab1:
        st.subheader("Add New Position (BUY)")
        with st.form("add_position_form", clear_on_submit=True):
            ticker = st.selectbox("ETF", data["etfs"])
            shares = st.number_input("Shares", min_value=0.0001, step=1.0, format="%.4f", value=0.0001)
            price = st.number_input("Price per Share", min_value=0.0001, step=0.01, format="%.4f", value=0.0001)
            date = st.date_input("Date", value=datetime.today())
            notes = st.text_input("Notes (optional)", value="")

            if st.form_submit_button("✅ Save Position"):
                if shares > 0 and price > 0:
                    new_id = max([t.get("id", 0) for t in data["transactions"]], default=0) + 1
                    data["transactions"].append({
                        "id": new_id,
                        "ticker": ticker,
                        "type": "BUY",
                        "shares": float(shares),
                        "price": float(price),
                        "date": str(date),
                        "notes": notes
                    })
                    save_data(data)
                    st.success(f"✅ Position added! {shares:.4f} shares of {ticker} at ${price:.4f}")
                    st.balloons()
                else:
                    st.error("Shares and Price must be greater than 0")

    with tab2:
        st.subheader("Sell Position")
        with st.form("sell_position_form", clear_on_submit=True):
            ticker = st.selectbox("ETF to Sell", data["etfs"], key="sell_ticker")
            pos = calculate_position(ticker, data)
            st.write(f"Current shares of {ticker}: **{pos['shares']:.4f}**")

            shares = st.number_input("Shares to Sell", min_value=0.0001, step=1.0, format="%.4f", value=0.0001, key="sell_shares")
            price = st.number_input("Sell Price per Share", min_value=0.0001, step=0.01, format="%.4f", value=0.0001, key="sell_price")
            date = st.date_input("Date", value=datetime.today(), key="sell_date")
            notes = st.text_input("Notes (optional)", value="", key="sell_notes")

            if st.form_submit_button("✅ Confirm Sell"):
                if shares > pos["shares"]:
                    st.error(f"You only have {pos['shares']:.4f} shares")
                elif shares > 0 and price > 0:
                    new_id = max([t.get("id", 0) for t in data["transactions"]], default=0) + 1
                    data["transactions"].append({
                        "id": new_id,
                        "ticker": ticker,
                        "type": "SELL",
                        "shares": float(shares),
                        "price": float(price),
                        "date": str(date),
                        "notes": notes
                    })
                    save_data(data)
                    st.success(f"✅ Sold {shares:.4f} shares of {ticker} at ${price:.4f}")
                else:
                    st.error("Shares and Price must be greater than 0")

    with tab3:
        st.subheader("Delete a Transaction")
        if data["transactions"]:
            st.dataframe(pd.DataFrame(data["transactions"]), use_container_width=True)
            delete_id = st.number_input("Enter Transaction ID to delete", min_value=1, step=1)
            if st.button("🗑️ Delete Transaction"):
                original_len = len(data["transactions"])
                data["transactions"] = [t for t in data["transactions"] if t.get("id") != delete_id]
                for i, t in enumerate(data["transactions"], 1):
                    t["id"] = i
                save_data(data)
                if len(data["transactions"]) < original_len:
                    st.success("✅ Transaction deleted")
                    st.rerun()
                else:
                    st.warning("ID not found")
        else:
            st.info("No transactions yet.")

# --------------------------
# ENTER / EDIT ROC
# --------------------------
elif page == "📥 Enter / Edit ROC":
    st.title("📥 Enter / Edit Distribution & ROC")

    tab1, tab2 = st.tabs(["Add New ROC", "Edit / Delete ROC"])

    with tab1:
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

        with st.form("distribution_form", clear_on_submit=True):
            ticker_index = data["etfs"].index(default_ticker) if default_ticker in data["etfs"] else 0
            ticker = st.selectbox("Select ETF", data["etfs"], index=ticker_index)
            dist_per_share = st.number_input("Distribution per Share ($)", min_value=0.0, value=float(default_dist), format="%.4f")
            roc_pct = st.number_input("ROC Percentage (%)", min_value=0.0, max_value=100.0, value=100.0, step=1.0, format="%.0f")
            dist_date = st.date_input("Date", value=datetime.today())

            if st.form_submit_button("✅ Save Distribution"):
                pos = calculate_position(ticker, data)
                shares = pos["shares"]
                roc_dollar = dist_per_share * (roc_pct / 100.0) * shares
                ordinary_dollar = dist_per_share * ((100 - roc_pct) / 100.0) * shares

                data["distributions"].append({
                    "id": max([d.get("id", 0) for d in data["distributions"]], default=0) + 1,
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

    with tab2:
        st.subheader("Delete ROC Entry")
        if data["distributions"]:
            for i, d in enumerate(data["distributions"], 1):
                if "id" not in d:
                    d["id"] = i
            save_data(data)

            st.dataframe(pd.DataFrame(data["distributions"]), use_container_width=True)
            delete_roc_id = st.number_input("Enter ROC ID to delete", min_value=1, step=1, key="del_roc")
            if st.button("🗑️ Delete ROC Entry"):
                original_len = len(data["distributions"])
                data["distributions"] = [d for d in data["distributions"] if d.get("id") != delete_roc_id]
                for i, d in enumerate(data["distributions"], 1):
                    d["id"] = i
                save_data(data)
                if len(data["distributions"]) < original_len:
                    st.success("✅ ROC entry deleted")
                    st.rerun()
                else:
                    st.warning("ID not found")
        else:
            st.info("No ROC entries yet.")

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
    c1.metric("Shares", f"{pos['shares']:.4f}")
    c2.metric("Avg Cost", f"${pos['avg_cost']:.4f}")
    c3.metric("Price", f"${current_price:.4f}" if current_price else "—")
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
            "Shares": f"{pos['shares']:.4f}",
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
            save_data(data)
            st.success(f"✅ Added ${add_amount:,.2f}")
            st.rerun()
    with col2:
        st.subheader("Remove Cash")
        remove_amount = st.number_input("Amount to Remove", min_value=0.0, step=50.0, key="remove_cash")
        if st.button("Remove Cash"):
            data["cash"] = max(0, data.get("cash", 0) - remove_amount)
            save_data(data)
            st.success(f"✅ Removed ${remove_amount:,.2f}")
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
    st.subheader("Currently Tracked ETFs")
    st.write(", ".join(data["etfs"]))
    st.divider()
    st.subheader("Add New ETF")
    new_ticker = st.text_input("New ETF Ticker").upper().strip()
    if st.button("➕ Add ETF"):
        if new_ticker and new_ticker not in data["etfs"]:
            data["etfs"].append(new_ticker)
            save_data(data)
            st.success(f"✅ Added {new_ticker}")
            st.rerun()
        elif new_ticker in data["etfs"]:
            st.warning("Already exists")
    st.divider()
    st.subheader("Delete ETF")
    if data["etfs"]:
        del_ticker = st.selectbox("Select ETF to remove", data["etfs"])
        if st.button("🗑️ Delete ETF"):
            data["etfs"] = [t for t in data["etfs"] if t != del_ticker]
            save_data(data)
            st.success(f"✅ Removed {del_ticker}")
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
                "Shares": f"{p['shares']:.4f}",
                "Avg Cost": f"{p['avg_cost']:.4f}",
                "Adjusted Cost": p["adjusted_cost"],
                "ROC Received": p["roc_total"]
            })
        if report_rows:
            rdf = pd.DataFrame(report_rows)
            st.dataframe(rdf, use_container_width=True)
            csv = rdf.to_csv(index=False).encode()
            st.download_button("Download CSV", csv, f"etf_report_{datetime.today().strftime('%Y%m%d')}.csv", "text/csv")
        else:
            st.warning("No positions found.")
