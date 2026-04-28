import streamlit as st
import psycopg2
import urllib.parse

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
    <p style="color: #636E72; font-weight: bold; letter-spacing: 2px;">POS & DIGITAL KHATA</p>
</div>
<br>
""", unsafe_allow_html=True)

# 4 TABS AB: POS, Inventory, Godaam, aur naya Udhar Khata
tab_pos, tab_inventory, tab_stock_view, tab_udhar = st.tabs(["🛒 Quick Bill", "📦 Add Stock", "📊 Godaam", "📒 Udhar Khata"])

# --- TAB 1: POS (With Udhar Integration) ---
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
            
            # --- PAYMENT METHOD ---
            pay_method = st.radio("💳 Payment Method", ["💸 Cash/UPI", "📝 Udhar (Credit)"], horizontal=True)
            cust_name, cust_phone = "", ""
            
            if pay_method == "📝 Udhar (Credit)":
                st.warning("Please enter customer details for Khata.")
                u_col1, u_col2 = st.columns(2)
                with u_col1:
                    cust_name = st.text_input("Customer Name *")
                with u_col2:
                    cust_phone = st.text_input("WhatsApp No. (Optional)")
            
            if st.button("✅ Generate Bill & Deduct Stock", use_container_width=True):
                if pay_method == "📝 Udhar (Credit)" and not cust_name.strip():
                    st.error("⚠️ Udhar ke liye naam likhna zaroori hai!")
                elif current_stock >= qty or is_flexible:
                    # 1. Deduct Stock
                    cursor.execute("UPDATE inventory_master SET stock_qty = stock_qty - %s WHERE item_name = %s", (qty, selected_name))
                    
                    # 2. Add to Udhar Khata (if selected)
                    if pay_method == "📝 Udhar (Credit)":
                        cursor.execute("""
                            INSERT INTO udhar_khata (customer_name, phone_number, total_due) 
                            VALUES (%s, %s, %s)
                            ON CONFLICT (customer_name) 
                            DO UPDATE SET total_due = udhar_khata.total_due + EXCLUDED.total_due,
                                          phone_number = COALESCE(EXCLUDED.phone_number, udhar_khata.phone_number);
                        """, (cust_name, cust_phone, total_bill))
                        st.success(f"Transaction Saved! ₹{total_bill} added to {cust_name}'s Khata.")
                    else:
                        st.success(f"Cash Transaction Saved! {qty}x {selected_name} sold.")
                    st.balloons()
                else:
                    st.error("⚠️ Stock is less than the quantity!")
        else:
            st.warning("No items in inventory. Add stock first!")
    except Exception as e:
        st.error(f"Error: {e}")

# --- TAB 2: ADD STOCK (Godaam Entry) ---
with tab_inventory:
    st.subheader("📥 Master Stock Entry")
    with st.form("add_stock_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Item Name")
            category = st.selectbox("Category", ["Packaged", "Cold Drinks", "Fruits", "Juice", "Other"])
            stock_added = st.number_input("Stock Added", min_value=0, step=1)
        with col2:
            purchase_price = st.number_input("Purchase Price (₹)", min_value=0.0, step=1.0)
            selling_price = st.number_input("Selling Price (₹)", min_value=0.0, step=1.0)
            item_type = st.radio("Pricing", ["Fixed MRP", "Flexible Price"])
        
        is_flex_val = True if item_type == "Flexible Price" else False
        if st.form_submit_button("📦 Save to Inventory", use_container_width=True):
            if new_name:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO inventory_master (item_name, category, stock_qty, purchase_price, selling_price, is_flexible_price) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (item_name) 
                    DO UPDATE SET stock_qty = inventory_master.stock_qty + EXCLUDED.stock_qty, 
                                  purchase_price = EXCLUDED.purchase_price, selling_price = EXCLUDED.selling_price;
                """, (new_name, category, stock_added, purchase_price, selling_price, is_flex_val))
                st.success("✅ Stock Updated!")

# --- TAB 3: VIEW GODAAM ---
with tab_stock_view:
    st.subheader("📊 Live Inventory")
    if st.button("🔄 Refresh Inventory"):
        st.rerun()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, stock_qty, purchase_price, selling_price FROM inventory_master ORDER BY stock_qty ASC")
        all_stock = cursor.fetchall()
        if all_stock:
            for item in all_stock:
                st.markdown(f"""
                <div style='background-color:#f8f9fa; color:#000000; padding:15px; border-radius:8px; margin-bottom:10px; border-left: 6px solid {"#28a745" if item[1] > 5 else "#dc3545"}; box-shadow: 0px 2px 4px rgba(0,0,0,0.1);'>
                    <strong style='font-size: 18px;'>{item[0]}</strong> <br>
                    <span style='color: #333333;'>Stock: <b>{item[1]}</b> | Margin: <b>₹{(item[3] - item[2]):.2f}</b></span>
                </div>
                """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error: {e}")

# --- TAB 4: UDHAR KHATA (THE NEW SYSTEM) ---
with tab_udhar:
    st.subheader("📒 Digital Udhar Khata")
    
    try:
        cursor = conn.cursor()
        # Sirf unko dikhao jinka udhar baki hai (>0)
        cursor.execute("SELECT customer_name, phone_number, total_due FROM udhar_khata WHERE total_due > 0 ORDER BY total_due DESC")
        udhar_list = cursor.fetchall()
        
        # Settle Payment Section
        st.markdown("### 💰 Receive Payment (Jama Karein)")
        if udhar_list:
            khata_names = [u[0] for u in udhar_list]
            settle_col1, settle_col2 = st.columns(2)
            with settle_col1:
                settle_name = st.selectbox("Select Customer", khata_names)
            with settle_col2:
                # Find current due for selected customer
                current_due = next(u[2] for u in udhar_list if u[0] == settle_name)
                st.info(f"Pending: ₹{current_due}")
                
            amount_received = st.number_input("Amount Received (₹)", min_value=1.0, max_value=float(current_due), step=1.0)
            
            if st.button("📥 Jama Karlein (Deduct from Khata)", use_container_width=True):
                cursor.execute("UPDATE udhar_khata SET total_due = total_due - %s WHERE customer_name = %s", (amount_received, settle_name))
                st.success(f"✅ ₹{amount_received} received from {settle_name}. Remaining due updated!")
                st.rerun()
                
            st.divider()
            
            # View All Pending Khata
            st.markdown("### 🔴 Pending Accounts")
            market_total = sum([u[2] for u in udhar_list])
            st.error(f"**Total Paisa Market Mein Hai: ₹{market_total}**")
            
            for u in udhar_list:
                c_name, c_phone, c_due = u[0], u[1], u[2]
                st.markdown(f"""
                <div style='background-color:#FFF3CD; color:#856404; padding:15px; border-radius:8px; margin-bottom:10px; border-left: 6px solid #FFC107; box-shadow: 0px 2px 4px rgba(0,0,0,0.1);'>
                    <strong style='font-size: 18px;'>👤 {c_name}</strong> <br>
                    <span style='font-size: 20px; font-weight: bold;'>Baki Hai: ₹{c_due}</span>
                </div>
                """, unsafe_allow_html=True)
                
                # WhatsApp Reminder Button
                if c_phone:
                    msg = f"Namaste {c_name} ji,\nVardhman Juice Center se aapka ₹{c_due} ka udhar baki hai. Kripya samay milne par jama karwa dein. 🙏"
                    wa_url = f"https://wa.me/91{c_phone}?text={urllib.parse.quote(msg)}"
                    st.markdown(f'<a href="{wa_url}" target="_blank" style="display: inline-block; background-color: #25D366; color: white; padding: 8px 12px; border-radius: 5px; text-decoration: none; font-size: 14px; margin-bottom: 15px;">📲 Send Reminder</a>', unsafe_allow_html=True)
                
        else:
            st.success("🎉 Market mein koi udhar baki nahi hai!")
            
    except Exception as e:
        st.error(f"Khata Error: {e}")
