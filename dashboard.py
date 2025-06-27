import streamlit as st
import mysql.connector
from mysql.connector import Error
from datetime import date
import pandas as pd

# --- UI Header ---
st.set_page_config(page_title="eBay Dashboard", layout="wide")
st.title("📦 eBay Sold Items Dashboard")

# --- Database Connection ---
try:
    db = mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"]
    )
    cursor = db.cursor(dictionary=True)
except Error as e:
    st.error(f"Database connection failed: {e}")
    st.stop()

# --- Handle product detail page ---
query_params = st.query_params
if "item_id" in query_params:
    item_id = query_params["item_id"]
    if isinstance(item_id, list):
        item_id = item_id[0]

    # Fetch item details
    cursor.execute("""
        SELECT ebay_item_number, title, price, product_url, sku, image_url
        FROM daily_sold_items
        WHERE ebay_item_number = %s
    """, (item_id,))
    item = cursor.fetchone()

    if item:
        st.header(item['title'])
        st.markdown(f"**SKU**: {item['sku'] or 'N/A'}")
        st.markdown(f"**Price**: ${item['price']:.2f}")
        st.markdown(f"**eBay Link**: [🔗 Link]({item['product_url']})")
        if item['image_url']:
            st.image(item['image_url'], width=400)

        # Show sold history
        cursor.execute("""
            SELECT sold_date, quantity_sold
            FROM item_sold_dates
            WHERE ebay_item_number = %s
            ORDER BY sold_date
        """, (item_id,))
        sold_history = cursor.fetchall()
        if sold_history:
            df_history = pd.DataFrame(sold_history)
            st.subheader("📅 Sold History")
            st.dataframe(df_history, use_container_width=True)
        else:
            st.info("No sold history available.")
    else:
        st.warning("Item not found.")
    st.stop()

# --- Session State ---
if 'running_query' not in st.session_state:
    st.session_state.running_query = False
if 'df_results' not in st.session_state:
    st.session_state.df_results = pd.DataFrame()

# --- Date Selection ---
mode = st.radio("Choose Mode", ["Single Date", "Date Range"])
if mode == "Single Date":
    selected_date = st.date_input("Select Date", date.today())
    start_date = end_date = selected_date
else:
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", date.today())
    with col2:
        end_date = st.date_input("End Date", date.today())

# --- Query Button ---
query_button = st.button("Run Query", disabled=st.session_state.running_query)

# --- Run Query ---
if query_button:
    st.session_state.running_query = True
    try:
        with st.spinner("🔍 Fetching sold items..."):
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')

            summary_query = """
                SELECT d.ebay_item_number, d.title, d.price, d.product_url, d.sku,
                       SUM(s.quantity_sold) AS total_quantity_sold
                FROM daily_sold_items d
                JOIN item_sold_dates s ON d.ebay_item_number = s.ebay_item_number
                WHERE s.sold_date BETWEEN %s AND %s
                GROUP BY d.ebay_item_number, d.title, d.price, d.product_url, d.sku
                ORDER BY total_quantity_sold DESC
            """
            cursor.execute(summary_query, (start_str, end_str))
            summary_results = cursor.fetchall()

            if summary_results:
                df_summary = pd.DataFrame(summary_results)
                st.session_state.df_results = df_summary
            else:
                st.session_state.df_results = pd.DataFrame()

    except Error as err:
        st.error(f"❌ MySQL Error: {err}")
        st.session_state.df_results = pd.DataFrame()

    finally:
        st.session_state.running_query = False

# --- Display Table and Filters ---
df = st.session_state.df_results
if not df.empty:
    st.success(f"✅ Found {len(df)} item(s)")

    # Filter UI
    with st.expander("🔍 Filter Results", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            title_filter = st.text_input("Filter by Title")
            sku_filter = st.text_input("Filter by SKU")
        with col2:
            price_min, price_max = float(df['price'].min()), float(df['price'].max())
            price_range = st.slider("Filter by Price", price_min, price_max, (price_min, price_max))

            qty_min, qty_max = int(df['total_quantity_sold'].min()), int(df['total_quantity_sold'].max())
            if qty_min < qty_max:
                qty_range = st.slider("Filter by Total Quantity Sold", qty_min, qty_max, (qty_min, qty_max))
            else:
                qty_range = (qty_min, qty_max)

    # Apply filters
    df_filtered = df.copy()
    if title_filter:
        df_filtered = df_filtered[df_filtered['title'].str.contains(title_filter, case=False, na=False, regex=False)]
    if sku_filter:
        df_filtered = df_filtered[df_filtered['sku'].str.contains(sku_filter, case=False, na=False, regex=False)]
    df_filtered = df_filtered[
        (df_filtered['price'] >= price_range[0]) & (df_filtered['price'] <= price_range[1]) &
        (df_filtered['total_quantity_sold'] >= qty_range[0]) & (df_filtered['total_quantity_sold'] <= qty_range[1])
    ]

    if not df_filtered.empty:
        # Pagination Setup
        items_per_page = 500
        total_pages = (len(df_filtered) - 1) // items_per_page + 1
        page = st.number_input("Page", 1, total_pages, 1, step=1)
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_data = df_filtered.iloc[start_idx:end_idx]

        # Display item summaries with clickable markdown
        for _, row in page_data.iterrows():
            with st.expander(f"{row['title']} (Sold: {row['total_quantity_sold']})"):
                st.markdown(f"**SKU**: {row['sku']}")
                st.markdown(f"**Price**: ${row['price']:.2f}")
                st.markdown(f"[🔗 View Product Page](/?item_id={row['ebay_item_number']})")

        # CSV Download of currently filtered results
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", data=csv, file_name="filtered_sold_items.csv", mime='text/csv')
    else:
        st.warning("⚠️ No items match the filters.")
else:
    st.info("ℹ️ Run a query to view results.")