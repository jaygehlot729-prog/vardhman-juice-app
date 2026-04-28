import streamlit as st
import psycopg2
import urllib.parse

# --- PAGE CONFIG ---
st.set_page_config(page_title="Vardhman Juice Center", page_icon="🍹", layout="wide")

# --- SECURE DATABASE CONNECTION ---
@st.cache_resource
def init_connection():
    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
    # This prevents the "current transaction is aborted" error forever
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
    <p style="color: #636E72; font-weight: bold; letter-spacing: 2px;">ADVANCED INVENTORY & POS</p>
</div>
<br>
""", unsafe_allow_html=True)

tab_pos, tab_inventory, tab_stock_view = st.tabs(["🛒 Quick Billing", "📦 Add Stock (Entry)", "📊 View Godaam"])

# --- TAB 1: POS (Billing & Stock Deduction) ---
with tab_pos:
    st.subheader("⚡ Fast Billing")
    
    try:
        cursor = conn.cursor()
        # Fetch items that have stock OR are flexible (like juice where stock might not be strictly counted)
        cursor.execute("SELECT item_name, selling_price, is_flexible_price, stock_qty FROM inventory_master ORDER BY item_name ASC")
        db_items = cursor.fetchall() 
        
        if db_items:
            item_names = [item[0] for item in db_items]
            selected_name = st.selectbox("🔍 Search & Select Product", item_names)
            
            current_item = next(item for item in db_items if item[0] == selected_name)
            base_price = float(current_item[1])
            is_flexible = current_item[2]
            current_stock = current_item[3]
            
            st.caption(f"Current Stock Available: **{current_stock} units**")
            
            col1, col2 = st.columns(2)
            with col1:
                qty = st.number_input("Quantity Sold", min_value=1, max_value=max(current_stock, 100), step=1)
            with col2:
                if is_flexible:
                    final_price = st.number_input("Price (Discountable for Juice/Fruits)", value=base_price, step=1.0)
                else:
                    st.info(f"🔒 Fixed Price (MRP): ₹{base_price}")
                    final_price = base_price
            
            total_bill = qty * final_price
            st.success(f"### Total Bill: ₹{total_bill}")
            
            if st.button("✅ Generate Bill & Deduct Stock", use_container_width=True):
                if current_stock >= qty or is_flexible:
                    # Deduct stock from database
                    cursor.execute("UPDATE inventory_master SET stock_qty = stock_qty - %s WHERE item_name = %s", (qty, selected_name))
                    st.success(f"Transaction Saved! {qty}x {selected_name} deducted from inventory.")
                    st.balloons()
                else:
                    st.error("⚠️ Stock is less than the quantity you are trying to sell!")
        else:
            st.warning("No items in inventory. Please add stock first!")
    except Exception as e:
        st.error(f"Error fetching data: {e}")

# --- TAB 2: ADD NEW STOCK (The Godaam Entry) ---
with tab_inventory:
    st.subheader("📥 Master Stock Entry (Maal Godaam)")
    st.info("Bhai, kal jab free hona tab yahan apni poori dukan ka saaman ek-ek karke feed kar dena.")
    
    with st.form("add_stock_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Item Name (e.g., Lays 20, Coconut, Mango)")
            category = st.selectbox("Category", ["Packaged Chips/Snacks", "Cold Drinks", "Fresh Fruits/Coconut", "Prepared Juice", "Other"])
            stock_added = st.number_input("Quantity Added to Shop", min_value=0, step=1)
        
        with col2:
            purchase_price = st.number_input("Purchase Price / Padi (₹ per piece)", min_value=0.0, step=1.0)
            selling_price = st.number_input("Selling Price / MRP (₹ per piece)", min_value=0.0, step=1.0)
            item_type = st.radio("Pricing Rules at Counter", ["Fixed MRP (Chips)", "Flexible Price (Fruits/Juice)"])
        
        is_flex_val = True if item_type == "Flexible Price (Fruits/Juice)" else False
        
        if st.form_submit_button("📦 Save to Inventory", use_container_width=True):
            if new_name:
                try:
                    cursor = conn.cursor()
                    # Use UPSERT: If item exists, update stock. If new, insert it.
                    cursor.execute("""
                        INSERT INTO inventory_master (item_name, category, stock_qty, purchase_price, selling_price, is_flexible_price) 
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (item_name) 
                        DO UPDATE SET stock_qty = inventory_master.stock_qty + EXCLUDED.stock_qty, 
                                      purchase_price = EXCLUDED.purchase_price,
                                      selling_price = EXCLUDED.selling_price;
                    """, (new_name, category, stock_added, purchase_price, selling_price, is_flex_val))
                    st.success(f"✅ {new_name} Successfully Added to Stock!")
                except Exception as e:
                    st.error(f"Database Save Error: {e}")

# --- TAB 3: VIEW GODAAM (Inventory Summary) ---
with tab_stock_view:
    st.subheader("📊 Live Shop Inventory & Profit Margins")
    if st.button("🔄 Refresh Data"):
        st.rerun()
        
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, stock_qty, purchase_price, selling_price FROM inventory_master ORDER BY stock_qty ASC")
        all_stock = cursor.fetchall()
        
        if all_stock:
            for item in all_stock:
                profit_per_piece = item[3] - item[2]
                st.markdown(f"""
                <div style='background-color:#f8f9fa; padding:10px; border-radius:5px; margin-bottom:5px; border-left: 5px solid {"#28a745" if item[1] > 5 else "#dc3545"};'>
                    <strong>{item[0]}</strong> <br>
                    Stock Left: {item[1]} units | Margin per piece: ₹{profit_per_piece:.2f} (Bought: ₹{item[2]} ➔ Sell: ₹{item[3]})
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("Godaam khali hai bhai.")
    except Exception as e:
        st.error(f"Could not load inventory: {e}")
