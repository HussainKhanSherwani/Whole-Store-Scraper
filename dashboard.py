import streamlit as st
import psycopg2
import pandas as pd

# --- UI Header ---
st.set_page_config(page_title="eBay Dashboard", layout="wide")
st.title("📦 eBay Sold Items Dashboard")

# --- Database Connection ---
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

try:
    conn = get_connection()
except Exception as e:
    st.error(f"Database Connection Failed: {e}")
    st.stop()

# --- Load Data from View ---
# We just grab the view directly. No complex joins needed anymore.
query = """
    WITH product_stats AS (
    -- This part replicates the VIEW logic
    SELECT 
        item_number,
        title,
        MAX(image_url) as image_url,
        MAX(price) as current_price,
        
        -- 7 Days
        SUM(CASE 
            WHEN sold_date >= CURRENT_DATE - INTERVAL '7 days' THEN 1 
            ELSE 0 
        END) AS sold_last_7_days,

        -- 14 Days
        SUM(CASE 
            WHEN sold_date >= CURRENT_DATE - INTERVAL '14 days' THEN 1 
            ELSE 0 
        END) AS sold_last_14_days,

        -- 21 Days
        SUM(CASE 
            WHEN sold_date >= CURRENT_DATE - INTERVAL '21 days' THEN 1 
            ELSE 0 
        END) AS sold_last_21_days,

        -- 30 Days
        SUM(CASE 
            WHEN sold_date >= CURRENT_DATE - INTERVAL '30 days' THEN 1 
            ELSE 0 
        END) AS sold_last_30_days,

        -- Total
        COUNT(*) AS total_sold_all_time

    FROM sales_raw
    GROUP BY item_number, title
)

-- This part replicates your final SELECT logic
SELECT 
    image_url,
    title,
    current_price,
    sold_last_7_days,
    sold_last_14_days,
    sold_last_21_days,
    sold_last_30_days,
    total_sold_all_time,
    item_number,
    
    -- Window Functions for Grand Totals
    SUM(total_sold_all_time) OVER() AS grand_total_sold,
    SUM(sold_last_7_days) OVER() AS grand_total_sold_7_days,
    SUM(sold_last_14_days) OVER() AS grand_total_sold_14_days,
    SUM(sold_last_21_days) OVER() AS grand_total_sold_21_days,
    SUM(sold_last_30_days) OVER() AS grand_total_sold_30_days

FROM product_stats
ORDER BY sold_last_7_days DESC, item_number ASC; 
-- Note: I kept 'item_number ASC' here to prevent the "inconsistent data" issue you faced earlier.
"""

# Run query
with st.spinner("Fetching Dashboard View..."):
    df = pd.read_sql(query, conn)

# --- Display The View ---
if not df.empty:
    
    # Optional: Simple Search Bar
    search = st.text_input("🔍 Search Product", "")
    if search:
        df = df[df['title'].str.contains(search, case=False, na=False)]

    # The Main Table
    st.dataframe(
        df,
        column_config={
            "image_url": st.column_config.ImageColumn("Image", width="small"),
            "title": st.column_config.TextColumn("Product Name", width="medium"),
            "current_price": st.column_config.NumberColumn("Price", format="$%.2f"),
            
            # The Columns you specifically asked for
            "sold_last_7_days": st.column_config.NumberColumn("7 Days", format="%d 📦"),
            "sold_last_14_days": st.column_config.NumberColumn("14 Days", format="%d"),
            "sold_last_21_days": st.column_config.NumberColumn("21 Days", format="%d"),
            "sold_last_30_days": st.column_config.NumberColumn("30 Days", format="%d"),
            "total_sold_all_time": st.column_config.NumberColumn("Total Sold", format="%d"),
            
            "item_number": st.column_config.TextColumn("Item ID"),
        },
        use_container_width=True,
        hide_index=True,
        height=900 
    )
else:
    st.warning("No data found in the view.")