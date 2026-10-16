import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Referral Analytics Dashboard", page_icon="📊", layout="wide")

st.title("📊 Referral Link Analytics Dashboard")
st.markdown("Track your campaign performance, clicks, and conversions in real-time.")

# 2. ROBUST DATABASE LOADER
def load_data():
    db_path = "tracker.db"
    
    # Check if database file exists
    if not os.path.exists(db_path):
        return None, "Database file 'tracker.db' not found. Make sure your FastAPI app has run at least once."
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Query to fetch all links and aggregate click/purchase events
        query = """
            SELECT 
                rl.id,
                rl.slug,
                rl.target_url,
                COUNT(ce.id) as total_clicks,
                SUM(CASE WHEN ce.status = 'purchased' THEN 1 ELSE 0 END) as total_purchases
            FROM referral_links rl
            LEFT JOIN click_events ce ON rl.id = ce.link_id
            GROUP BY rl.id, rl.slug, rl.target_url
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df, None
        
    except Exception as e:
        return None, f"Database error (Tables might not be created yet): {str(e)}"

# Load data with error check
df, error_message = load_data()

if error_message:
    st.warning(f"⚠️ {error_message}")
    st.info("💡 **Tip:** Make sure your FastAPI app has been run (`uvicorn main:app --reload`) and you have created at least one link using the `/create-link/` endpoint.")
else:
    # Handle NaN values for links with 0 clicks
    df['total_clicks'] = df['total_clicks'].fillna(0)
    df['total_purchases'] = df['total_purchases'].fillna(0)
    
    # Calculate Conversion Rate (%)
    df['conversion_rate'] = df.apply(
        lambda row: (row['total_purchases'] / row['total_clicks'] * 100) if row['total_clicks'] > 0 else 0.0, 
        axis=1
    )

    # Refresh button
    if st.button("🔄 Refresh Data"):
        st.rerun()

    # 3. TOP-LEVEL METRICS (KPI Cards)
    total_clicks_all = df['total_clicks'].sum()
    total_purchases_all = df['total_purchases'].sum()
    overall_conversion = (total_purchases_all / total_clicks_all * 100) if total_clicks_all > 0 else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Clicks Across All Links", int(total_clicks_all))
    col2.metric("Total Purchases", int(total_purchases_all))
    col3.metric("Overall Conversion Rate", f"{overall_conversion:.2f}%")

    st.markdown("---")

    # 4. VISUALIZATIONS (Charts)
    if df.empty or total_clicks_all == 0:
        st.info("No click data found yet! Create a link using FastAPI docs (`/docs`) and click it a few times.")
    else:
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Clicks vs. Purchases by Link")
            df_melted = df.melt(id_vars=['slug'], value_vars=['total_clicks', 'total_purchases'], 
                                var_name='Metric', value_name='Count')
            df_melted['Metric'] = df_melted['Metric'].replace({'total_clicks': 'Clicks', 'total_purchases': 'Purchases'})
            
            fig_bar = px.bar(df_melted, x='slug', y='Count', color='Metric', barmode='group',
                             title="Performance per Referral Link", text_auto=True)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_right:
            st.subheader("Conversion Rate (%) by Link")
            fig_conv = px.bar(df, x='slug', y='conversion_rate', 
                              title="Conversion Rate Percentage", text=df['conversion_rate'].apply(lambda x: f"{x:.1f}%"),
                              color='conversion_rate', color_continuous_scale='Blues')
            st.plotly_chart(fig_conv, use_container_width=True)

        # 5. DETAILED DATA TABLE
        st.subheader("📋 Detailed Breakdown")
        st.dataframe(df[['slug', 'target_url', 'total_clicks', 'total_purchases', 'conversion_rate']], use_container_width=True)