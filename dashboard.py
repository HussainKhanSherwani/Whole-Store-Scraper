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
    SELECT 
        *
    FROM product_performance_view
    ORDER BY sold_last_7_days DESC
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
        use_container_width=True,
        hide_index=True,
        height=900 
    )
else:
    st.warning("No data found in the view.")