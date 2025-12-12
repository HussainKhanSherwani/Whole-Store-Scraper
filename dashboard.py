import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta

# --- UI Header ---
st.set_page_config(page_title="eBay Dashboard", layout="wide")
st.title("📦 eBay Sold Items Dashboard")

# --- 1. Sidebar Controls (Date Range & Filters) ---
with st.sidebar:
    st.header("📅 Custom Date Range")
    default_start = date.today() - timedelta(days=3)
    default_end = date.today()
    
    start_date = st.date_input("Start Date", default_start)
    end_date = st.date_input("End Date", default_end)
    
    st.divider()
    st.header("🔍 Sales Filters (Min Sold)")
    
    min_7   = st.number_input("Min Sales (7 Days)", min_value=0, value=0)
    min_14  = st.number_input("Min Sales (14 Days)", min_value=0, value=0)
    min_21  = st.number_input("Min Sales (21 Days)", min_value=0, value=0)
    min_30  = st.number_input("Min Sales (30 Days)", min_value=0, value=0)
    min_custom = st.number_input(f"Min Sales ({start_date} to {end_date})", min_value=0, value=0)
    min_total = st.number_input("Min Total Sold", min_value=0, value=0)

# --- 2. Database Connection ---
@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        port=st.secrets["postgres"]["port"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"],
        dbname=st.secrets["postgres"]["database"],
        sslmode='require'
    )

# --- 3. Load Data ---
@st.cache_data(ttl=600)
def load_data(start_d, end_d):
    conn = get_connection()
    
    query = """
        WITH latest_data AS (
            SELECT DISTINCT ON (item_number)
                item_number, price, title, image_url, product_url -- ADDED product_url HERE
            FROM sales_raw
            ORDER BY item_number, sold_date DESC
        ),
        sales_counts AS (
            SELECT 
                item_number,
                
                -- Standard Metrics
                SUM(CASE WHEN sold_date >= CURRENT_DATE - INTERVAL '7 days' THEN 1 ELSE 0 END) AS sold_last_7_days,
                SUM(CASE WHEN sold_date >= CURRENT_DATE - INTERVAL '14 days' THEN 1 ELSE 0 END) AS sold_last_14_days,
                SUM(CASE WHEN sold_date >= CURRENT_DATE - INTERVAL '21 days' THEN 1 ELSE 0 END) AS sold_last_21_days,
                SUM(CASE WHEN sold_date >= CURRENT_DATE - INTERVAL '30 days' THEN 1 ELSE 0 END) AS sold_last_30_days,
                COUNT(*) AS total_sold_all_time,

                -- CUSTOM RANGE COLUMN
                SUM(CASE 
                    WHEN sold_date >= %s AND sold_date <= %s THEN 1 
                    ELSE 0 
                END) AS sold_custom_range

            FROM sales_raw
            GROUP BY item_number
        )
        SELECT 
            l.image_url, l.title, l.price AS current_price, l.product_url, -- ADDED product_url HERE
            s.sold_last_7_days, s.sold_last_14_days, s.sold_last_21_days, 
            s.sold_last_30_days, s.total_sold_all_time, s.sold_custom_range,
            l.item_number
        FROM sales_counts s
        JOIN latest_data l ON s.item_number = l.item_number
        ORDER BY s.sold_last_7_days DESC, l.item_number ASC;
    """
    
    return pd.read_sql(query, conn, params=(start_d, end_d))

try:
    with st.spinner("Fetching Data..."):
        df = load_data(start_date, end_date)
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# --- 4. Apply Filters ---
if not df.empty:
    
    df_filtered = df[
        (df['sold_last_7_days'] >= min_7) &
        (df['sold_last_14_days'] >= min_14) &
        (df['sold_last_21_days'] >= min_21) &
        (df['sold_last_30_days'] >= min_30) &
        (df['sold_custom_range'] >= min_custom) &
        (df['total_sold_all_time'] >= min_total)
    ]

    search = st.text_input("🔍 Search Product by Title", "")
    if search:
        df_filtered = df_filtered[df_filtered['title'].str.contains(search, case=False, na=False)]

    # --- 5. Display Table ---
    custom_col_label = f"Sales ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d')})"
    st.markdown(f"### Showing {len(df_filtered)} items")
    
    st.dataframe(
        df_filtered,
        column_config={
            "image_url": st.column_config.ImageColumn("Image", width="small"),
            
            # --- NEW LINK COLUMN CONFIGURATION ---
            "product_url": st.column_config.LinkColumn(
                "Link", 
                display_text="Open 🔗"  # This text appears instead of the long URL
            ),
            # -------------------------------------

            "title": st.column_config.TextColumn("Product Name", width="medium"),
            "current_price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "sold_last_7_days": st.column_config.NumberColumn("7 Days", format="%d"),
            "sold_last_14_days": st.column_config.NumberColumn("14 Days", format="%d"),
            "sold_last_21_days": st.column_config.NumberColumn("21 Days", format="%d"),
            "sold_last_30_days": st.column_config.NumberColumn("30 Days", format="%d"),
            
            "sold_custom_range": st.column_config.NumberColumn(
                custom_col_label, 
                help=f"Sales between {start_date} and {end_date}",
                format="%d ⭐"
            ),
            "total_sold_all_time": st.column_config.NumberColumn("Total Sold", format="%d"),
            "item_number": st.column_config.TextColumn("Item ID"),
        },
        column_order=[
            "image_url", "product_url", "title", "current_price",  # Added product_url here
            "sold_custom_range",
            "sold_last_7_days", "sold_last_14_days", "sold_last_21_days", "sold_last_30_days", 
            "total_sold_all_time", "item_number"
        ],
        use_container_width=True,
        hide_index=True,
        height=900 
    )
else:
    st.warning("No data found.")