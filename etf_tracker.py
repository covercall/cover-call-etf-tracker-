import streamlit as st
import pandas as pd
import json
import os
import hashlib
from datetime import datetime, date
import yfinance as yf
import plotly.express as px

DATA_FILE = "portfolio_data.json"
DEFAULT_ETFS = ["QQQI", "SPYI", "XSPI", "XQQI", "BTCI", "XBCI", "GIAX", "BLOX", "MLPI", "SLJY", "IAUI"]

st.set_page_config(page_title="Covered Call ETF Tracker", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

if "theme" not in st.session_state:
    st.session_state.theme = "Dark"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def apply_theme():
    if st.session_state.theme == "Dark":
        st.markdown("""
        <style>
        .stApp { background-color: #0e1117; color: #ffffff; }
        section[data-testid="stSidebar"] { background-color: #161b22; color: #ffffff; }
        h1, h2, h3, h4, h5, h6 { color: #ffffff !important; }
        [data-testid="stMetricValue"] { color: #ffffff !important; }
        [data-testid="stMetricLabel"] { color: #cccccc !important; }
        .stSelectbox div[data-baseweb="select"] > div { background-color: #21262d !important; color: #ffffff !important; }
        .stSelectbox div[data-baseweb="select"] span { color: #ffffff !important; }
        .stTextInput > div > div > input, .stNumberInput > div > div > input, .stDateInput > div > div > input {
            background-color: #21262d !important; color: #ffffff !important;
        }
        .stButton > button { background-color: #238636; color: white; border: none; }
        .stButton > button:hover { background-color: #2ea043; color: white; }
        p, span, label, div { color: #e6edf3 !important; }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""<style>.stApp { background-color: #ffffff; color: #1f2328; }</style>""", unsafe_allow_html=True)

apply_theme()

def fmt(x):
    try:
        x = float(x)
        if abs(x - round(x)) < 1e-9:
            return f"{x:.1f}"
        if abs(x - round(x, 1)) < 1e-9:
            return f"{x:.1f}"
        return f"{x:.2f}"
    except:
        return "—"

def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {
        "transactions": [],
        "distributions": [],
        "cash": 0.0,
        "etfs": DEFAULT_ETFS.copy(),
        "pin_hash": None
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
            return dividends.index[-1].strftime("%Y-%m-%d"), round(float(dividends.iloc[-1]), 4)
    except:
        pass
    return None, None

def calculate_position(ticker, data):
    buys = [t for t in data["transactions"] if t.get("ticker") == ticker and t.get("type") == "BUY"]
    sells = [t for t in data["transactions"] if t.get("ticker") == ticker and t.get("type") == "SELL"]

    shares_bought = sum(float(t.get("shares", 0)) for t in buys)
    shares_sold = sum(float(t.get("shares", 0)) for t in sells)
    total_shares = shares_bought - shares_sold

    cost_bought = sum(float(t.get("shares", 0)) * float(t.get("price", 0)) for t in buys)
    cost_sold = sum(float(t.get("shares", 0)) * float(t.get("price", 0)) for t in sells)
    total_cost = cost_bought - cost_sold

    roc_total = sum(float(d.get("roc_amount", 0)) for d in data["distributions"] if d.get("ticker") == ticker)
    ordinary_total = sum(float(d.get("ordinary_amount", 0)) for d in data["distributions"] if d.get("ticker") == ticker)
    adjusted_cost = max(total_cost - roc_total, 0)
    avg_cost = total_cost / total_shares if total_shares > 0 else 0

    return {
        "shares": round(total_shares, 4),
        "total_cost": round(total_cost, 2),
        "adjusted_cost": round(adjusted_cost, 2),
        "avg_cost": round(avg_cost, 2),
        "roc_total": round(roc_total, 2),
        "ordinary_total": round(ordinary_total, 2)
    }

def parse_date(d):
    try:
        return datetime.strptime(str(d)[:10], "%Y-%m-%d").date()
    except:
        return None

data = load_data()
if "pin_hash" not in data:
    data["pin_hash"] = None

# ======================
# PIN LOCK SCREEN
# ======================
if not st.session_state.authenticated:
    st.title("🔒 ETF Tracker Locked")

    # First time: set PIN
    if not data.get("pin_hash"):
        st.subheader("Set your 4-digit PIN")
        st.caption("This is the first time. Create a PIN to protect your portfolio.")
        pin1 = st.text_input("Enter 4-digit PIN", type="password", max_chars=4)
        pin2 = st.text_input("Confirm PIN", type="password", max_chars=4)

        if st.button("Set PIN"):
            if not pin1.isdigit() or len(pin1) != 4:
                st.error("PIN must be exactly 4 digits")
            elif pin1 != pin2:
                st.error("PINs do not match")
            else:
                data["pin_hash"] = hash_pin(pin1)
                save_data(data)
                st.session_state.authenticated = True
                st.success("✅ PIN set successfully")
                st.rerun()
    else:
        # Normal unlock
        st.subheader("Enter your 4-digit PIN")
        pin = st.text_input("PIN", type="password", max_chars=4)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Unlock"):
                if pin.isdigit() and len(pin) == 4 and hash_pin(pin) == data.get("pin_hash"):
                    st.session_state.authenticated = True
                    st.success("✅ Unlocked")
                    st.rerun()
                else:
                    st.error("Wrong PIN")
        with col2:
            if st.button("Reset PIN (needs backup restore later)"):
                st.warning("To reset PIN you must restore a backup that has no PIN, or clear app data. Prefer unlocking with the correct PIN.")

    st.stop()

# ======================
# APP (only after unlock)
# ======================
st.sidebar.title("📊 ETF Tracker")
theme_choice = st.sidebar.radio("Theme", ["Dark", "Light"], index=0 if st.session_state.theme == "Dark" else 1)
if theme_choice != st.session_state.theme:
    st.session_state.theme = theme_choice
    st.rerun()

if st.sidebar.button("🔒 Lock App"):
    st.session_state.authenticated = False
    st.rerun()

page = st.sidebar.radio("Menu", [
    "🏠 Portfolio Overview",
    "➕ Add / Edit Positions",
    "📥 Enter / Edit ROC",
    "🔍 Ticker Details",
    "📅 Dividend Calendar",
    "📈 Charts & Projection",
    "💰 Cash",
    "💾 Backup / Restore",
    "🔐 Change PIN",
    "📰 News",
    "⚙️ Manage ETFs",
    "📄 Reports"
])

if st.sidebar.button("🔄 Refresh Prices"):
    st.rerun()

# ======================
# CHANGE PIN
# ======================
if page == "🔐 Change PIN":
    st.title("🔐 Change PIN")
    old = st.text_input("Current PIN", type="password", max_chars=4)
    new1 = st.text_input("New 4-digit PIN", type="password", max_chars=4)
    new2 = st.text_input("Confirm new PIN", type="password", max_chars=4)

    if st.button("Update PIN"):
        if not old.isdigit() or hash_pin(old) != data.get("pin_hash"):
            st.error("Current PIN is wrong")
        elif not new1.isdigit() or len(new1) != 4:
            st.error("New PIN must be exactly 4 digits")
        elif new1 != new2:
            st.error("New PINs do not match")
        else:
            data["pin_hash"] = hash_pin(new1)
            save_data(data)
            st.success("✅ PIN updated")

# ======================
# PORTFOLIO OVERVIEW
# ======================
elif page == "🏠 Portfolio Overview":
    st.title("📊 Portfolio Overview")

    overview_rows = []
    total_market_value = 0.0
    total_cost_sum = 0.0
    total_adjusted_cost = 0.0
    total_ordinary = 0.0
    total_roc_income = 0.0

    for ticker in sorted(data["etfs"]):
        pos = calculate_position(ticker, data)
        if pos["shares"] <= 0:
            continue

        price = get_current_price(ticker) or 0.0
        market_value = pos["shares"] * price
        pnl = market_value - pos["adjusted_cost"]
        pnl_pct = (pnl / pos["adjusted_cost"] * 100) if pos["adjusted_cost"] != 0 else 0.0

        overview_rows.append({
            "Ticker": f"${ticker}",
            "Shares": fmt(pos["shares"]),
            "Avg Cost": fmt(pos["avg_cost"]),
            "Market Price": fmt(price) if price else "—",
            "Total Cost": fmt(pos["total_cost"]),
            "Market Value": fmt(market_value),
            "Adjusted Cost": fmt(pos["adjusted_cost"]),
            "P&L $": fmt(pnl),
            "P&L %": f"{pnl_pct:.1f}%",
            "ROC Applied": fmt(pos["roc_total"]),
            "Ordinary": fmt(pos["ordinary_total"])
        })

        total_market_value += market_value
        total_cost_sum += pos["total_cost"]
        total_adjusted_cost += pos["adjusted_cost"]
        total_ordinary += pos["ordinary_total"]
        total_roc_income += pos["roc_total"]

    df = pd.DataFrame(overview_rows)

    def style_pnl(row):
        styles = [""] * len(row)
        try:
            pnl_val = float(str(row["P&L $"]).replace(",", ""))
            color = "color: #3fb950; font-weight: bold" if pnl_val > 0 else ("color: #f85149; font-weight: bold" if pnl_val < 0 else "")
            styles[df.columns.get_loc("P&L $")] = color
            styles[df.columns.get_loc("P&L %")] = color
        except:
            pass
        return styles

    if not df.empty:
        st.dataframe(df.style.apply(style_pnl, axis=1), use_container_width=True)
    else:
        st.info("No positions yet.")

    st.divider()
    st.subheader("Portfolio Summary")

    total_pnl = total_market_value - total_adjusted_cost
    total_pnl_pct = (total_pnl / total_adjusted_cost * 100) if total_adjusted_cost != 0 else 0.0
    total_income = total_ordinary + total_roc_income

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Cost (Paid)", f"${fmt(total_cost_sum)}")
    c2.metric("Total Market Value", f"${fmt(total_market_value)}")
    c3.metric("Adjusted Cost (after ROC)", f"${fmt(total_adjusted_cost)}")
    if total_pnl > 0:
        c4.metric("Unrealized P&L $", f"${fmt(total_pnl)}", delta=f"+{fmt(total_pnl)}", delta_color="normal")
    elif total_pnl < 0:
        c4.metric("Unrealized P&L $", f"${fmt(total_pnl)}", delta=f"{fmt(total_pnl)}", delta_color="inverse")
    else:
        c4.metric("Unrealized P&L $", f"${fmt(total_pnl)}")

    c5, c6, c7 = st.columns(3)
    if total_pnl > 0:
        c5.metric("Total P&L %", f"{total_pnl_pct:+.1f}%", delta=f"{total_pnl_pct:+.1f}%", delta_color="normal")
    elif total_pnl < 0:
        c5.metric("Total P&L %", f"{total_pnl_pct:+.1f}%", delta=f"{total_pnl_pct:+.1f}%", delta_color="inverse")
    else:
        c5.metric("Total P&L %", f"{total_pnl_pct:+.1f}%")

    if total_income > 0:
        c6.metric("Total Income", f"${fmt(total_income)}", delta=f"Ord ${fmt(total_ordinary)} | ROC ${fmt(total_roc_income)}", delta_color="normal")
    else:
        c6.metric("Total Income", f"${fmt(total_income)}", delta=f"Ord ${fmt(total_ordinary)} | ROC ${fmt(total_roc_income)}")
    c7.metric("Cash", f"${fmt(data.get('cash', 0))}")

# --------------------------
# ADD / EDIT POSITIONS
# --------------------------
elif page == "➕ Add / Edit Positions":
    st.title("➕ Add / Edit Positions")
    tab1, tab2, tab3 = st.tabs(["Add Position", "Sell Position", "Delete Transaction"])

    with tab1:
        with st.form("add_position_form", clear_on_submit=True):
            ticker_options = [""] + data["etfs"]
            ticker = st.selectbox("ETF", ticker_options, index=0, format_func=lambda x: "Select ETF..." if x == "" else x)
            shares = st.number_input("Shares", min_value=0.0, step=1.0, format="%.1f", value=0.0)
            price = st.number_input("Price per Share", min_value=0.0, step=0.01, format="%.2f", value=0.0)
            date_val = st.date_input("Date", value=datetime.today())
            notes = st.text_input("Notes (optional)", value="")
            if st.form_submit_button("✅ Save Position"):
                if ticker == "":
                    st.error("Please select an ETF")
                elif shares > 0 and price > 0:
                    new_id = max([int(t.get("id", 0)) for t in data["transactions"]], default=0) + 1
                    data["transactions"].append({
                        "id": new_id, "ticker": ticker, "type": "BUY",
                        "shares": float(shares), "price": float(price),
                        "date": str(date_val), "notes": notes
                    })
                    save_data(data)
                    st.success(f"✅ Position added! {fmt(shares)} shares of ${ticker} at ${fmt(price)}")
                    st.balloons()
                else:
                    st.error("Shares and Price must be greater than 0")

    with tab2:
        with st.form("sell_position_form", clear_on_submit=True):
            ticker_options = [""] + data["etfs"]
            ticker = st.selectbox("ETF to Sell", ticker_options, index=0, format_func=lambda x: "Select ETF..." if x == "" else x, key="sell_ticker")
            if ticker:
                pos = calculate_position(ticker, data)
                st.write(f"Current shares of ${ticker}: **{fmt(pos['shares'])}**")
            shares = st.number_input("Shares to Sell", min_value=0.0, step=1.0, format="%.1f", value=0.0, key="sell_shares")
            price = st.number_input("Sell Price", min_value=0.0, step=0.01, format="%.2f", value=0.0, key="sell_price")
            date_val = st.date_input("Date", value=datetime.today(), key="sell_date")
            notes = st.text_input("Notes (optional)", value="", key="sell_notes")
            if st.form_submit_button("✅ Confirm Sell"):
                if ticker == "":
                    st.error("Please select an ETF")
                else:
                    pos = calculate_position(ticker, data)
                    if shares > pos["shares"]:
                        st.error(f"You only have {fmt(pos['shares'])} shares")
                    elif shares > 0 and price > 0:
                        new_id = max([int(t.get("id", 0)) for t in data["transactions"]], default=0) + 1
                        data["transactions"].append({
                            "id": new_id, "ticker": ticker, "type": "SELL",
                            "shares": float(shares), "price": float(price),
                            "date": str(date_val), "notes": notes
                        })
                        save_data(data)
                        st.success(f"✅ Sold {fmt(shares)} shares of ${ticker}")
                    else:
                        st.error("Shares and Price must be greater than 0")

    with tab3:
        if data["transactions"]:
            st.dataframe(pd.DataFrame(data["transactions"]), use_container_width=True)
            delete_id = st.number_input("Transaction ID to delete", min_value=1, step=1)
            if st.button("🗑️ Delete Transaction"):
                original_len = len(data["transactions"])
                data["transactions"] = [t for t in data["transactions"] if int(t.get("id", 0)) != delete_id]
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
    tab1, tab2 = st.tabs(["Add New ROC", "Delete ROC"])

    with tab1:
        helper_ticker = st.selectbox("Check last dividend for:", data["etfs"], key="helper")
        if "last_div_amount" not in st.session_state:
            st.session_state.last_div_amount = None
            st.session_state.last_div_ticker = None

        if st.button("Get Last Dividend from Yahoo"):
            last_date, last_amount = get_last_dividend(helper_ticker)
            if last_amount:
                st.session_state.last_div_amount = last_amount
                st.session_state.last_div_ticker = helper_ticker
                st.success(f"✅ Last dividend for **{helper_ticker}**: **${last_amount}** on {last_date}")
            else:
                st.warning("Could not find recent dividend data.")

        if st.session_state.last_div_amount is not None:
            st.info(f"Ready: **{st.session_state.last_div_ticker}** → ${st.session_state.last_div_amount}")
            if st.button("✅ Use this dividend amount"):
                st.session_state.fill_dist = st.session_state.last_div_amount
                st.session_state.fill_ticker = st.session_state.last_div_ticker

        st.divider()
        default_ticker = st.session_state.get("fill_ticker", "")
        default_dist = st.session_state.get("fill_dist", 0.0)
        ticker_options = [""] + data["etfs"]

        with st.form("distribution_form", clear_on_submit=True):
            ticker = st.selectbox(
                "Select ETF", ticker_options,
                index=ticker_options.index(default_ticker) if default_ticker in ticker_options else 0,
                format_func=lambda x: "Select ETF..." if x == "" else x
            )
            dist_per_share = st.number_input("Distribution per Share ($)", min_value=0.0, value=float(default_dist), format="%.4f")
            roc_pct = st.number_input("ROC Percentage (%)", min_value=0.0, max_value=100.0, value=100.0, step=1.0, format="%.0f")
            dist_date = st.date_input("Date", value=datetime.today())

            if st.form_submit_button("✅ Save Distribution"):
                if ticker == "":
                    st.error("Please select an ETF")
                else:
                    pos = calculate_position(ticker, data)
                    shares = pos["shares"]
                    roc_dollar = dist_per_share * (roc_pct / 100.0) * shares
                    ordinary_dollar = dist_per_share * ((100 - roc_pct) / 100.0) * shares
                    new_id = max([int(d.get("id", 0)) for d in data["distributions"]], default=0) + 1
                    data["distributions"].append({
                        "id": new_id, "ticker": ticker, "date": str(dist_date),
                        "distribution_per_share": dist_per_share, "roc_percent": roc_pct,
                        "roc_amount": round(roc_dollar, 2),
                        "ordinary_amount": round(ordinary_dollar, 2),
                        "shares_at_time": shares
                    })
                    save_data(data)
                    st.success(f"✅ Saved | ROC: {roc_pct:.0f}% | Reduction: ${fmt(roc_dollar)}")
                    st.session_state.fill_dist = 0.0
                    st.session_state.fill_ticker = None
                    st.rerun()

    with tab2:
        if data["distributions"]:
            st.dataframe(pd.DataFrame(data["distributions"]), use_container_width=True)
            delete_roc_id = st.number_input("ROC ID to delete", min_value=1, step=1, key="del_roc")
            if st.button("🗑️ Delete ROC Entry"):
                original_len = len(data["distributions"])
                data["distributions"] = [d for d in data["distributions"] if int(d.get("id", 0)) != delete_roc_id]
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

    st.subheader(f"${selected}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Shares", fmt(pos["shares"]))
    c2.metric("Avg Cost", f"${fmt(pos['avg_cost'])}")
    c3.metric("Market Price", f"${fmt(current_price)}" if current_price else "—")
    c4.metric("Market Value", f"${fmt(pos['shares'] * current_price)}" if current_price else "—")

    st.markdown("#### Transactions (Buy & Sell)")
    txs = [t for t in data["transactions"] if t.get("ticker") == selected]
    if txs:
        st.dataframe(pd.DataFrame(txs), use_container_width=True)
        st.markdown("#### Edit a Transaction")
        edit_id = st.number_input("Transaction ID to edit", min_value=1, step=1, key="edit_id")
        tx_to_edit = next((t for t in data["transactions"] if int(t.get("id", 0)) == edit_id), None)
        if tx_to_edit:
            with st.form("edit_tx_form"):
                st.write(f"Editing ID {edit_id} — {tx_to_edit.get('type')} {tx_to_edit.get('ticker')}")
                new_shares = st.number_input("Shares", value=float(tx_to_edit.get("shares", 0)), format="%.1f")
                new_price = st.number_input("Price", value=float(tx_to_edit.get("price", 0)), format="%.2f")
                new_date = st.date_input("Date", value=datetime.strptime(str(tx_to_edit.get("date", datetime.today().date()))[:10], "%Y-%m-%d").date())
                new_notes = st.text_input("Notes", value=tx_to_edit.get("notes", ""))
                if st.form_submit_button("✅ Save Changes"):
                    tx_to_edit["shares"] = float(new_shares)
                    tx_to_edit["price"] = float(new_price)
                    tx_to_edit["date"] = str(new_date)
                    tx_to_edit["notes"] = new_notes
                    save_data(data)
                    st.success("✅ Transaction updated")
                    st.rerun()
    else:
        st.info("No transactions for this ticker.")

    st.markdown("#### Distributions")
    dists = [d for d in data["distributions"] if d.get("ticker") == selected]
    st.dataframe(pd.DataFrame(dists) if dists else pd.DataFrame(), use_container_width=True)

# --------------------------
# DIVIDEND CALENDAR
# --------------------------
elif page == "📅 Dividend Calendar":
    st.title("📅 Dividend Calendar")
    if data["distributions"]:
        dist_df = pd.DataFrame(data["distributions"])
        dist_df["date"] = pd.to_datetime(dist_df["date"])
        st.dataframe(dist_df.sort_values("date", ascending=False), use_container_width=True)
    else:
        st.info("No distributions recorded yet.")

# --------------------------
# CHARTS & PROJECTION
# --------------------------
elif page == "📈 Charts & Projection":
    st.title("📈 Charts & Income Projection")
    projection_data = []
    for ticker in data["etfs"]:
        pos = calculate_position(ticker, data)
        if pos["shares"] <= 0:
            continue
        ticker_dists = [d for d in data["distributions"] if d.get("ticker") == ticker]
        if ticker_dists:
            latest = sorted(ticker_dists, key=lambda x: x.get("date", ""), reverse=True)[0]
            monthly = float(latest.get("distribution_per_share", 0)) * pos["shares"]
            weekly, yearly = monthly / 4.33, monthly * 12
        else:
            monthly = weekly = yearly = 0
        projection_data.append({
            "Ticker": f"${ticker}", "Shares": fmt(pos["shares"]),
            "Weekly": fmt(weekly), "Monthly": fmt(monthly), "Yearly": fmt(yearly)
        })

    if projection_data:
        proj_df = pd.DataFrame(projection_data)
        st.dataframe(proj_df, use_container_width=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Weekly", f"${fmt(sum(float(r['Weekly']) for r in projection_data))}")
        c2.metric("Total Monthly", f"${fmt(sum(float(r['Monthly']) for r in projection_data))}")
        c3.metric("Total Yearly", f"${fmt(sum(float(r['Yearly']) for r in projection_data))}")
    else:
        st.info("No data to project yet.")

    st.divider()
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
    st.metric("Current Cash Balance", f"${fmt(data.get('cash', 0))}")
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        add_amount = st.number_input("Amount to Add", min_value=0.0, step=50.0, key="add_cash")
        if st.button("Add Cash"):
            data["cash"] = data.get("cash", 0) + add_amount
            save_data(data)
            st.success(f"✅ Added ${fmt(add_amount)}")
            st.rerun()
    with col2:
        remove_amount = st.number_input("Amount to Remove", min_value=0.0, step=50.0, key="remove_cash")
        if st.button("Remove Cash"):
            data["cash"] = max(0, data.get("cash", 0) - remove_amount)
            save_data(data)
            st.success(f"✅ Removed ${fmt(remove_amount)}")
            st.rerun()

# --------------------------
# BACKUP / RESTORE
# --------------------------
elif page == "💾 Backup / Restore":
    st.title("💾 Backup / Restore Data")
    st.markdown("Download a backup before updates. Upload it later to restore your data.")
    st.subheader("Download Backup")
    st.download_button(
        "⬇️ Download Backup File",
        json.dumps(data, indent=2),
        f"etf_tracker_backup_{datetime.today().strftime('%Y%m%d_%H%M')}.json",
        "application/json"
    )
    st.divider()
    st.subheader("Upload Backup (Restore)")
    uploaded_file = st.file_uploader("Choose backup file", type=["json"])
    if uploaded_file is not None:
        try:
            uploaded_data = json.load(uploaded_file)
            if st.button("🔄 Restore This Backup"):
                save_data(uploaded_data)
                st.success("✅ Data restored successfully!")
                st.balloons()
                st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {e}")

# --------------------------
# NEWS
# --------------------------
elif page == "📰 News":
    st.title("📰 ETF News")
    selected_news = st.selectbox("Select ETF", data["etfs"])
    try:
        news = yf.Ticker(selected_news).news
        if news:
            for item in news[:6]:
                st.markdown(f"**{item.get('title', 'No title')}**")
                if item.get("link"):
                    st.markdown(f"[Read more]({item['link']})")
                st.markdown("---")
        else:
            st.info("No recent news found for this ETF.")
    except:
        st.warning("Could not load news.")

# --------------------------
# MANAGE ETFs
# --------------------------
elif page == "⚙️ Manage ETFs":
    st.title("⚙️ Manage ETFs")
    st.write("Currently tracked:", ", ".join(data["etfs"]))
    st.divider()
    new_ticker = st.text_input("Add new ETF").upper().strip()
    if st.button("➕ Add ETF"):
        if new_ticker and new_ticker not in data["etfs"]:
            data["etfs"].append(new_ticker)
            save_data(data)
            st.success(f"✅ Added {new_ticker}")
            st.rerun()
    st.divider()
    if data["etfs"]:
        del_ticker = st.selectbox("Delete ETF", data["etfs"])
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
    st.write(f"**Report generated:** {datetime.today().strftime('%d %b %Y %H:%M')}")

    report_type = st.radio(
        "Report period",
        ["All time", "Australian tax year (1 Jul – 30 Jun)", "Custom date range"],
        horizontal=True
    )

    start_date = None
    end_date = None

    if report_type == "Australian tax year (1 Jul – 30 Jun)":
        today = date.today()
        if today.month >= 7:
            tax_start = date(today.year, 7, 1)
            tax_end = date(today.year + 1, 6, 30)
        else:
            tax_start = date(today.year - 1, 7, 1)
            tax_end = date(today.year, 6, 30)

        year_options = [f"{y}-{y+1} (1 Jul {y} → 30 Jun {y+1})" for y in range(today.year - 3, today.year + 2)]
        default_label = f"{tax_start.year}-{tax_end.year} (1 Jul {tax_start.year} → 30 Jun {tax_end.year})"
        choice = st.selectbox("Select tax year", year_options, index=year_options.index(default_label) if default_label in year_options else 0)
        start_y = int(choice.split("-")[0])
        start_date = date(start_y, 7, 1)
        end_date = date(start_y + 1, 6, 30)
        st.caption(f"Period: {start_date.strftime('%d %b %Y')} → {end_date.strftime('%d %b %Y')}")

    elif report_type == "Custom date range":
        col_a, col_b = st.columns(2)
        with col_a:
            start_date = st.date_input("From", value=date(date.today().year, 7, 1))
        with col_b:
            end_date = st.date_input("To", value=date.today())

    if st.button("Generate Report"):
        filtered_dists = data["distributions"]
        if start_date and end_date:
            filtered_dists = []
            for d in data["distributions"]:
                dd = parse_date(d.get("date"))
                if dd and start_date <= dd <= end_date:
                    filtered_dists.append(d)

        report_rows = []
        sum_ordinary = 0.0
        sum_roc = 0.0

        for t in sorted(data["etfs"]):
            p = calculate_position(t, data)
            ordinary = sum(float(d.get("ordinary_amount", 0)) for d in filtered_dists if d.get("ticker") == t)
            roc = sum(float(d.get("roc_amount", 0)) for d in filtered_dists if d.get("ticker") == t)
            sum_ordinary += ordinary
            sum_roc += roc

            if p["shares"] > 0 or ordinary > 0 or roc > 0:
                report_rows.append({
                    "ETF": f"${t}",
                    "Shares": fmt(p["shares"]),
                    "Avg Cost": fmt(p["avg_cost"]),
                    "Total Cost": fmt(p["total_cost"]),
                    "Adjusted Cost (after ROC)": fmt(p["adjusted_cost"]),
                    "ROC in period": fmt(roc),
                    "Ordinary in period": fmt(ordinary)
                })

        if report_rows:
            rdf = pd.DataFrame(report_rows)
            st.dataframe(rdf, use_container_width=True)
            st.markdown("---")
            st.subheader("Totals for selected period")
            t1, t2, t3 = st.columns(3)
            t1.metric("Total Ordinary Dividends", f"${fmt(sum_ordinary)}")
            t2.metric("Total ROC", f"${fmt(sum_roc)}")
            t3.metric("Total Income (Ord + ROC)", f"${fmt(sum_ordinary + sum_roc)}")
            st.caption(f"Report generated: {datetime.today().strftime('%d %b %Y %H:%M')}")
            if start_date and end_date:
                st.caption(f"Period: {start_date.strftime('%d %b %Y')} → {end_date.strftime('%d %b %Y')}")
            st.download_button("Download CSV", rdf.to_csv(index=False).encode(), f"etf_report_{datetime.today().strftime('%Y%m%d')}.csv", "text/csv")
            st.success("✅ Report generated")
        else:
            st.warning("No data found for this period.")
