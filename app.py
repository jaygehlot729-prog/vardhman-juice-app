import streamlit as st
import psycopg2
import urllib.parse

# --- PAGE CONFIG ---
st.set_page_config(page_title="Vardhman Juice Center", page_icon="🍹", layout="wide")

# --- SECURE DATABASE CONNECTION ---
@st.cache_resource
def init_connection():
    # Ye cloud database (Supabase) se connect karega
    return psycopg2.connect(st.secrets["DATABASE_URL"])

try:
    conn = init_connection()
except Exception as e:
    st.error(f"Database connect nahi hua, settings check karo: {e}")
    st.stop()

# --- HEADER (Premium Look) ---
st.markdown("""
<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>
<div style="background: linear-gradient(135deg, #FF9A9E 0%, #FECFEF 100%); padding: 20px; border-radius: 15px; text-align: center; box-shadow: 0px 4px 15px rgba(0,0,0,0.1);">
    <h1 style="color: #2D3436; margin: 0; font-family: 'Arial Black', sans-serif;">🍹 VARDHMAN JUICE CENTER</h1>
    <p style="color: #636E72; font-weight: bold; letter-spacing: 2px;">LIVE CLOUD POS SYSTEM</p>
</div>
<br>
""", unsafe_allow_html=True)

tab_pos, tab_master = st.tabs(["🛒 Quick Billing", "🛠️ Add New Items"])

# --- TAB 1: POS (Fetching from Cloud) ---
with tab_pos:
    st.subheader("⚡ Fast Billing")
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, selling_price, is_juice FROM products")
        db_items = cursor.fetchall() 
        
        if db_items:
            item_names = [item[0] for item in db_items]
            selected_name = st.selectbox("🔍 Search & Select Product", item_names)
            
            current_item = next(item for item in db_items if item[0] == selected_name)
            base_price = float(current_item[1])
            is_juice = current_item[2]
            
            col1, col2 = st.columns(2)
            with col1:
                qty = st.number_input("Quantity", min_value=1, step=1)
            with col2:
                if is_juice:
                    final_price = st.number_input("Price (Discountable)", value=base_price, step=1.0)
                else:
                    st.info(f"🔒 Fixed Price: ₹{base_price}")
                    final_price = base_price
            
            total_bill = qty * final_price
            st.success(f"### Total Bill: ₹{total_bill}")
            
            if st.button("✅ Generate VIP Bill", use_container_width=True):
                msg = f"🧾 *VARDHMAN JUICE CENTER*\n\n*Item:* {selected_name}\n*Qty:* {qty}\n*Total:* ₹{total_bill}\n\n_Thank you for visiting!_ 🍹"
                wa_url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
                st.markdown(f'<a href="{wa_url}" target="_blank" style="display: block; text-align: center; background-color: #25D366; color: white; padding: 12px; border-radius: 8px; text-decoration: none; font-weight: bold;">📲 Send Bill on WhatsApp</a>', unsafe_allow_html=True)
        else:
            st.warning("Khali hai! Pehle 'Add New Items' mein jao aur saaman add karo.")
    except Exception as e:
        st.error(f"Error: {e}")

# --- TAB 2: ADD ITEMS TO CLOUD ---
with tab_master:
    st.subheader("🆕 Add New Item to Shop")
    with st.form("add_item", clear_on_submit=True):
        new_name = st.text_input("Item Name")
        new_brand = st.selectbox("Brand", ["Lays", "Amul", "Coke", "Fresh Juice", "Other"])
        new_price = st.number_input("Selling Price (₹)", min_value=0.0, step=1.0)
        item_type = st.radio("Type", ["Locked (MRP)", "Editable (Juice)"])
        
        is_juice_val = True if item_type == "Editable (Juice)" else False
        
        if st.form_submit_button("➕ Save to Cloud", use_container_width=True):
            if new_name:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO products (item_name, brand, selling_price, is_juice) VALUES (%s, %s, %s, %s)", 
                               (new_name, new_brand, new_price, is_juice_val))
                conn.commit()
                st.success(f"✅ {new_name} added to Cloud!")
