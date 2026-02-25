"""
PFM Dashboard — Streamlit UI for HUMO Card finance.db
Connects to: ~/Library/Mobile Documents/com~apple~CloudDocs/abror/Attachments/finance.db
Table: expenses (id, date, time, amount, currency, category, merchant,
                  payment_method, transaction_type, source, raw_text, tags,
                  created_at, is_enriched, enriched_category, ...)
"""

import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

DB_PATHS = [
    # Obsidian iCloud path (primary)
    Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/My Docs/Attachments/finance.db",
    # iCloud drive path variant
    Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/abror/Attachments/finance.db",
    # Docker container path (if running inside container)
    Path("/data/obsidian/Attachments/finance.db"),
    # Fallback: same directory as this script
    Path(__file__).parent / "finance.db",
]

CATEGORY_COLORS = {
    "FOOD": "#FF6B6B",
    "TRANSPORT": "#4ECDC4",
    "SHOPPING": "#45B7D1",
    "HEALTH": "#96CEB4",
    "UTILITIES": "#FECA57",
    "TELECOM": "#FF9FF3",
    "ATM": "#A29BFE",
    "TRANSFER": "#74B9FF",
    "OTHER": "#636E72",
}

st.set_page_config(
    page_title="💳 PFM Dashboard",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Dark-friendly CSS overrides
st.markdown(
    """
    <style>
    [data-testid="metric-container"] {
        background: #1e2130;
        border: 1px solid #2d3250;
        border-radius: 12px;
        padding: 16px 20px;
    }
    [data-testid="metric-container"] > div { color: #e0e0e0; }
    [data-testid="stDataFrame"] { border-radius: 10px; }
    .block-container { padding-top: 2rem; }
    h1 { font-size: 1.8rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ──────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────

def find_db() -> Optional[Path]:
    for p in DB_PATHS:
        if p.exists():
            return p
    return None


@st.cache_data(ttl=60)
def load_expenses() -> pd.DataFrame:
    db = find_db()
    if db is None:
        return pd.DataFrame()

    con = sqlite3.connect(db)
    df = pd.read_sql_query(
        """
        SELECT
            id,
            date,
            time,
            amount,
            currency,
            COALESCE(NULLIF(enriched_category, ''), category, 'OTHER') AS category,
            COALESCE(NULLIF(merchant, ''), 'Unknown') AS merchant,
            payment_method,
            COALESCE(card_last4,
                CASE WHEN payment_method LIKE '%*%'
                     THEN SUBSTR(payment_method, INSTR(payment_method, '*') + 1)
                     ELSE NULL END
            ) AS card_last4,
            transaction_type,
            source,
            is_enriched,
            llm_confidence,
            raw_text
        FROM expenses
        ORDER BY date DESC, time DESC
        """,
        con,
    )
    con.close()

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["category"] = df["category"].str.upper().fillna("OTHER")
    return df


def get_current_month_df(df: pd.DataFrame) -> pd.DataFrame:
    now = pd.Timestamp.now()
    return df[
        (df["date"].dt.year == now.year)
        & (df["date"].dt.month == now.month)
        & (df["transaction_type"] == "debit")
    ]


# ──────────────────────────────────────────────
# Layout helpers
# ──────────────────────────────────────────────

def fmt_uzs(amount: float) -> str:
    """Format UZS with thousand separators."""
    return f"{amount:,.0f} UZS"


def kpi_cards(df_month: pd.DataFrame) -> None:
    total = df_month["amount"].sum()
    top_cat = (
        df_month.groupby("category")["amount"].sum().idxmax()
        if not df_month.empty
        else "—"
    )
    top_cat_amount = (
        df_month.groupby("category")["amount"].sum().max()
        if not df_month.empty
        else 0
    )
    tx_count = len(df_month)
    avg_tx = total / tx_count if tx_count else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💸 Траты за месяц", fmt_uzs(total))
    col2.metric("🏆 Топ категория", top_cat, fmt_uzs(top_cat_amount))
    col3.metric("🔢 Транзакций", tx_count)
    col4.metric("📊 Средний чек", fmt_uzs(avg_tx))


def bar_by_day(df_month: pd.DataFrame) -> go.Figure:
    if df_month.empty:
        return go.Figure().add_annotation(text="Нет данных за этот месяц", showarrow=False)

    by_day = (
        df_month.groupby(df_month["date"].dt.date)["amount"]
        .sum()
        .reset_index()
        .rename(columns={"date": "Дата", "amount": "Сумма (UZS)"})
    )

    fig = px.bar(
        by_day,
        x="Дата",
        y="Сумма (UZS)",
        title="Траты по дням (текущий месяц)",
        color_discrete_sequence=["#4ECDC4"],
        template="plotly_dark",
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=40, b=20, l=0, r=0),
        xaxis_title=None,
        yaxis_title=None,
        hovermode="x unified",
    )
    fig.update_traces(
        hovertemplate="%{x}<br><b>%{y:,.0f} UZS</b><extra></extra>"
    )
    return fig


def donut_by_category(df_month: pd.DataFrame) -> go.Figure:
    if df_month.empty:
        return go.Figure().add_annotation(text="Нет данных", showarrow=False)

    by_cat = (
        df_month.groupby("category")["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=False)
    )

    colors = [CATEGORY_COLORS.get(c, "#95A5A6") for c in by_cat["category"]]

    fig = go.Figure(
        go.Pie(
            labels=by_cat["category"],
            values=by_cat["amount"],
            hole=0.55,
            marker_colors=colors,
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} UZS<br>%{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        title="По категориям",
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=40, b=20, l=0, r=0),
        showlegend=True,
        legend=dict(orientation="v", x=1.02, y=0.5),
    )
    return fig


def transactions_table(df: pd.DataFrame) -> None:
    last20 = (
        df[df["transaction_type"] == "debit"]
        .head(20)[["date", "amount", "currency", "category", "merchant", "card_last4", "is_enriched"]]
        .copy()
    )
    last20["date"] = last20["date"].dt.strftime("%Y-%m-%d")
    last20["amount"] = last20["amount"].apply(lambda x: f"{x:,.0f}")
    last20["card_last4"] = last20["card_last4"].apply(lambda x: f"*{x}" if pd.notna(x) else "—")
    last20["is_enriched"] = last20["is_enriched"].map({1: "✅", 0: "🔄"})
    last20.columns = ["Дата", "Сумма", "Валюта", "Категория", "Мерчант", "Карта", "LLM"]
    st.dataframe(last20, use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main() -> None:
    st.title("💳 Personal Finance Manager")

    db_path = find_db()
    if db_path:
        st.caption(f"База данных: `{db_path}`")
    else:
        st.error(
            "❌ finance.db не найдена. Убедись, что iCloud синхронизирован "
            "или укажи правильный путь в DB_PATHS."
        )
        return

    df = load_expenses()

    if df.empty:
        st.warning("⚠️ Таблица `expenses` пуста — транзакций пока нет.")
        st.info("Отправь уведомление от HUMO Card в Telegram, и бот запишет первую транзакцию.")
        return

    # ── Sidebar filters ───────────────────────
    with st.sidebar:
        st.header("🔍 Фильтры")

        # Card filter
        all_cards = sorted(df["card_last4"].dropna().unique().tolist())
        card_options = ["Все карты"] + [f"*{c}" for c in all_cards]
        selected_card_label = st.selectbox("💳 Карта", card_options)
        selected_card = None if selected_card_label == "Все карты" else selected_card_label[1:]

        st.divider()
        st.header("📈 За всё время")

    # Apply card filter
    if selected_card:
        df = df[df["card_last4"] == selected_card]

    df_month = get_current_month_df(df)

    # Show active filter hint
    if selected_card:
        st.info(f"Фильтр: карта *{selected_card}")

    # ── KPI row ──────────────────────────────
    st.subheader("Текущий месяц")
    kpi_cards(df_month)

    st.divider()

    # ── Charts ───────────────────────────────
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        st.plotly_chart(bar_by_day(df_month), use_container_width=True)

    with col_right:
        st.plotly_chart(donut_by_category(df_month), use_container_width=True)

    st.divider()

    # ── Last 20 transactions ──────────────────
    st.subheader("Последние 20 транзакций")

    enriched_count = int(df["is_enriched"].sum())
    total_count = len(df)
    col_a, col_b = st.columns([4, 1])
    with col_b:
        st.metric("LLM обогащено", f"{enriched_count}/{total_count}")

    transactions_table(df)

    # ── Sidebar: all-time stats ───────────────
    with st.sidebar:
        all_debits = df[df["transaction_type"] == "debit"]
        st.metric("Всего трат", fmt_uzs(all_debits["amount"].sum()))
        st.metric("Всего транзакций", len(all_debits))

        # Cards breakdown
        if len(all_cards) > 1:
            st.subheader("По картам")
            card_totals = (
                all_debits.groupby("card_last4")["amount"]
                .sum()
                .sort_values(ascending=False)
            )
            for card, amt in card_totals.items():
                label = f"*{card}" if pd.notna(card) else "Неизвестно"
                st.write(f"**{label}** — {fmt_uzs(amt)}")

        st.subheader("По категориям")
        cat_totals = (
            all_debits.groupby("category")["amount"]
            .sum()
            .sort_values(ascending=False)
        )
        for cat, amt in cat_totals.items():
            st.write(f"**{cat}** — {fmt_uzs(amt)}")

        st.divider()
        if st.button("🔄 Обновить данные"):
            st.cache_data.clear()
            st.rerun()


if __name__ == "__main__":
    main()
