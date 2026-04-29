import streamlit as st
import psycopg2
import urllib.parse
from datetime import datetime
import pytz

# --- PAGE CONFIG ---
st.set_page_config(page_title="Vardhman Juice Center", page_icon="🍹", layout="wide")

# --- SECURE DATABASE CONNECTION ---
@st.cache_resource
def init_connection():
    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
    conn.autocommit = True 
    return conn

try:
    conn = init_connection()
except Exception as e:
    st.error(f"Database connection failed: {e}")
    st.stop()

# --- HEADER ---
st.markdown("""
<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>
<div style="background: linear-gradient(135deg, #FF9A9E 0%, #FECFEF 100%); padding: 20px; border-radius: 15px; text-align: center; box-shadow: 0px 4px 15px rgba(0,0,0,0.1);">
    <h1 style="color: #2D3436; margin: 0; font-family: 'Arial Black', sans-serif;">🍹 VARDHMAN JUICE CENTER</h1>
    <p style="color: #636E72; font-weight: bold; letter-spacing: 2px;">MASTER POS SYSTEM</p>
</div>
<br>
""", unsafe_allow_html=True)

# 6 TABS AB: POS, Add Stock, Edit/Fix, Godaam, Khata, Galla
tab_pos, tab_inventory, tab_edit, tab_stock_view, tab_udhar, tab_galla = st.tabs(["🛒 Bill", "📦 Add Stock", "✏️ Fix/Edit", "📊 Godaam", "📒 Khata", "💰 Galla"])

# --- BRAND CATEGORIES ---
BRAND_LIST = [
    "Amul", "Balaji", "Aakash", "Haldiram", "Smoodh", "Parle Agro", 
    "Coca Cola", "Maaza", "Parle", "Colgate", "Clinic Plus", "Rin", 
    "Fresh Fruits / Coconut", "Prepared Juice", "Others"
]

# --- TAB 1: POS (Billing & Galla Entry) ---
with tab_pos:
    st.subheader("⚡ Fast Billing")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, selling_price, is_flexible_price, stock_qty FROM inventory_master ORDER BY item_name ASC")
        db_items = cursor.fetchall() 
        
        if db_items:
            item_names = [item[0] for item in db_items]
            selected_name = st.selectbox("🔍 Select Product", item_names)
            
            current_item = next(item for item in db_items if item[0] == selected_name)
            base_price, is_flexible, current_stock = float(current_item[1]), current_item[2], current_item[3]
            
            st.caption(f"Stock: **{current_stock} units**")
            
            col1, col2 = st.columns(2)
            with col1:
                qty = st.number_input("Qty", min_value=1, step=1)
            with col2:
                if is_flexible:
                    final_price = st.number_input("Price (Discountable)", value=base_price, step=1.0)
                else:
                    st.info(f"🔒 Fixed: ₹{base_price}")
                    final_price = base_price
            
            total_bill = qty * final_price
            st.success(f"### Total: ₹{total_bill}")
            
            st.divider()
            
            pay_method = st.radio("💳 Payment Method", ["💸 Cash/UPI", "📝 Udhar (Credit)"], horizontal=True)
            cust_name, cust_phone = "", ""
            
            if pay_method == "📝 Udhar (Credit)":
                st.warning("Please enter customer details for Khata.")
                u_col1, u_col2 = st.columns(2)
                with u_col1:
                    cust_name = st.text_input("Customer Name *")
                with u_col2:
                    cust_phone = st.text_input("WhatsApp No. (Optional)")
            
            if st.button("✅ Generate Bill", use_container_width=True):
                if pay_method == "📝 Udhar (Credit)" and not cust_name.strip():
                    st.error("⚠️ Udhar ke liye naam likhna zaroori hai!")
                elif current_stock >= qty or is_flexible:
                    cursor.execute("UPDATE inventory_master SET stock_qty = stock_qty - %s WHERE item_name = %s", (qty, selected_name))
                    cursor.execute("INSERT INTO daily_sales (item_name, qty, amount, pay_mode) VALUES (%s, %s, %s, %s)", 
                                   (selected_name, qty, total_bill, pay_method))
                    if pay_method == "📝 Udhar (Credit)":
                        cursor.execute("""
                            INSERT INTO udhar_khata (customer_name, phone_number, total_due) 
                            VALUES (%s, %s, %s)
                            ON CONFLICT (customer_name) 
                            DO UPDATE SET total_due = udhar_khata.total_due + EXCLUDED.total_due,
                                          phone_number = COALESCE(EXCLUDED.phone_number, udhar_khata.phone_number);
                        """, (cust_name, cust_phone, total_bill))
                        st.success(f"✅ ₹{total_bill} added to {cust_name}'s Khata!")
                    else:
                        st.success(f"✅ Cash Transaction Saved!")
                    st.balloons()
                else:
                    st.error("⚠️ Stock is less than the quantity!")
        else:
            st.warning("No items in inventory. Add stock first!")
    except Exception as e:
        st.error(f"Error: {e}")

# --- TAB 2: ADD STOCK ---
with tab_inventory:
    st.subheader("📥 Add New Stock")
    with st.form("add_stock_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Item Name (e.g. Haldiram Bhujia 10)")
            category = st.selectbox("Brand / Category", BRAND_LIST)
            stock_added = st.number_input("Stock Added (Quantity)", min_value=0, step=1)
        with col2:
            purchase_price = st.number_input("Purchase Price (Padi ₹)", min_value=0.0, step=1.0)
            selling_price = st.number_input("Selling Price (MRP ₹)", min_value=0.0, step=1.0)
            item_type = st.radio("Pricing Rule", ["Fixed MRP", "Flexible Price"])
        
        is_flex_val = True if item_type == "Flexible Price" else False
        if st.form_submit_button("📦 Save to Godaam", use_container_width=True):
            if new_name:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO inventory_master (item_name, category, stock_qty, purchase_price, selling_price, is_flexible_price) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (item_name) 
                    DO UPDATE SET stock_qty = inventory_master.stock_qty + EXCLUDED.stock_qty, 
                                  purchase_price = EXCLUDED.purchase_price, selling_price = EXCLUDED.selling_price;
                """, (new_name, category, stock_added, purchase_price, selling_price, is_flex_val))
                st.success("✅ Stock Updated Successfully!")

# --- TAB 3: EDIT / FIX ITEMS (THE NEW UPDATE) ---
with tab_edit:
    st.subheader("✏️ Edit or Delete Items (Galti Theek Karein)")
    st.info("Agar koi naam, price, ya quantity galat type ho gayi hai, toh yahan se theek karein.")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, category, stock_qty, purchase_price, selling_price FROM inventory_master ORDER BY item_name ASC")
        edit_items = cursor.fetchall()
        
        if edit_items:
            item_names_edit = [item[0] for item in edit_items]
            selected_edit_name = st.selectbox("🔍 Select Item to Fix", item_names_edit, key="edit_select")
            
            curr_item = next(item for item in edit_items if item[0] == selected_edit_name)
            
            st.markdown(f"**Current Stock:** {curr_item[2]} units | **Current Sell Price:** ₹{curr_item[4]}")
            
            new_edit_name = st.text_input("Edit Item Name", value=curr_item[0], key="edit_name")
            
            try:
                cat_index = BRAND_LIST.index(curr_item[1])
            except ValueError:
                cat_index = len(BRAND_LIST) - 1 # Defaults to 'Others'
                
            new_edit_category = st.selectbox("Edit Brand/Category", BRAND_LIST, index=cat_index, key="edit_cat")
            new_edit_stock = st.number_input("Correct Stock Quantity (Replace old qty)", value=int(curr_item[2]), step=1, key="edit_qty")
            new_edit_pp = st.number_input("Correct Purchase Price (₹)", value=float(curr_item[3]), step=1.0, key="edit_pp")
            new_edit_sp = st.number_input("Correct Selling Price (₹)", value=float(curr_item[4]), step=1.0, key="edit_sp")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Update Item Details", use_container_width=True, type="primary"):
                    cursor.execute("""
                        UPDATE inventory_master 
                        SET item_name=%s, category=%s, stock_qty=%s, purchase_price=%s, selling_price=%s
                        WHERE item_name=%s
                    """, (new_edit_name, new_edit_category, new_edit_stock, new_edit_pp, new_edit_sp, selected_edit_name))
                    st.success(f"✅ {new_edit_name} ki details successfully update ho gayi hain! (Refresh karke check karein)")
                    
            with col2:
                if st.button("🗑️ Delete Entire Item", use_container_width=True):
                    cursor.execute("DELETE FROM inventory_master WHERE item_name=%s", (selected_edit_name,))
                    st.error(f"🗑️ {selected_edit_name} godaam se poori tarah delete ho gaya hai!")
        else:
            st.write("Godaam mein abhi koi item nahi hai.")
    except Exception as e:
        st.error(f"Error: {e}")

# --- TAB 4: VIEW GODAAM ---
with tab_stock_view:
    st.subheader("📊 Live Godaam Inventory")
    if st.button("🔄 Refresh Inventory"):
        st.rerun()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, stock_qty, purchase_price, selling_price, category FROM inventory_master ORDER BY stock_qty ASC")
        all_stock = cursor.fetchall()
        if all_stock:
            for item in all_stock:
                st.markdown(f"""
                <div style='background-color:#f8f9fa; color:#000000; padding:15px; border-radius:8px; margin-bottom:10px; border-left: 6px solid {"#28a745" if item[1] > 5 else "#dc3545"}; box-shadow: 0px 2px 4px rgba(0,0,0,0.1);'>
                    <strong style='font-size: 18px;'>{item[0]}</strong> <span style='color: gray; font-size: 14px;'>({item[4]})</span><br>
                    <span style='color: #333333;'>Stock: <b>{item[1]}</b> | Margin: <b>₹{(item[3] - item[2]):.2f}</b></span>
                </div>
                """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error: {e}")

# --- TAB 5: UDHAR KHATA ---
with tab_udhar:
    st.subheader("📒 Digital Udhar Khata")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT customer_name, phone_number, total_due FROM udhar_khata WHERE total_due > 0 ORDER BY total_due DESC")
        udhar_list = cursor.fetchall()
        
        if udhar_list:
            khata_names = [u[0] for u in udhar_list]
            st.markdown("### 💰 Receive Payment")
            settle_col1, settle_col2 = st.columns(2)
            with settle_col1:
                settle_name = st.selectbox("Select Customer", khata_names)
            with settle_col2:
                current_due = next(u[2] for u in udhar_list if u[0] == settle_name)
                st.info(f"Pending: ₹{current_due}")
                
            amount_received = st.number_input("Amount Received (₹)", min_value=1.0, max_value=float(current_due), step=1.0)
            if st.button("📥 Jama Karlein", use_container_width=True):
                cursor.execute("UPDATE udhar_khata SET total_due = total_due - %s WHERE customer_name = %s", (amount_received, settle_name))
                st.success(f"✅ ₹{amount_received} received from {settle_name}.")
                st.rerun()
            
            st.divider()
            st.markdown("### 🔴 Pending Accounts")
            st.error(f"**Total Market Udhar: ₹{sum([u[2] for u in udhar_list])}**")
            for u in udhar_list:
                st.markdown(f"<div style='background-color:#FFF3CD; color:#856404; padding:10px; border-radius:5px; margin-bottom:5px; border-left: 5px solid #FFC107;'><strong>{u[0]}</strong>: Baki ₹{u[2]}</div>", unsafe_allow_html=True)
        else:
            st.success("🎉 Koi udhar baki nahi hai!")
    except Exception as e:
        st.error(f"Khata Error: {e}")

# --- TAB 6: AAJ KA GALLA ---
with tab_galla:
    st.subheader("💰 Aaj Ka Galla (Daily Report)")
    if st.button("🔄 Refresh Galla"):
        st.rerun()
        
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pay_mode, SUM(amount) 
            FROM daily_sales 
            WHERE sale_date = (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kolkata')::date 
            GROUP BY pay_mode
        """)
        sales_data = cursor.fetchall()
        
        total_cash, total_udhar = 0, 0
        for row in sales_data:
            if row[0] == '💸 Cash/UPI':
                total_cash = row[1]
            elif row[0] == '📝 Udhar (Credit)':
                total_udhar = row[1]
        
        st.markdown(f"""
        <div style='display: flex; gap: 10px; margin-bottom: 20px;'>
            <div style='flex: 1; background-color:#d4edda; color:#155724; padding:20px; border-radius:10px; text-align:center; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);'>
                <h3 style='margin:0; font-size:16px;'>💸 Cash / UPI</h3>
                <h1 style='margin:0; font-size:32px;'>₹{total_cash}</h1>
            </div>
            <div style='flex: 1; background-color:#f8d7da; color:#721c24; padding:20px; border-radius:10px; text-align:center; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);'>
                <h3 style='margin:0; font-size:16px;'>📝 Udhar</h3>
                <h1 style='margin:0; font-size:32px;'>₹{total_udhar}</h1>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.info(f"**Total Bikri Aaj Ki: ₹{total_cash + total_udhar}**")
        
        st.divider()
        st.markdown("### 🛒 Aaj Kya-Kya Bika?")
        cursor.execute("""
            SELECT item_name, SUM(qty), SUM(amount) 
            FROM daily_sales 
            WHERE sale_date = (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kolkata')::date 
            GROUP BY item_name ORDER BY SUM(qty) DESC
        """)
        items_sold = cursor.fetchall()
        if items_sold:
            for item in items_sold:
                st.markdown(f"🔸 **{item[0]}** - Bika: {item[1]} unit (Total: ₹{item[2]})")
        else:
            st.write("Aaj abhi tak koi bill nahi bana hai (Boni baaki hai!)")
    except Exception as e:
        st.error(f"Error fetching Galla: {e}")
