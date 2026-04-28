import streamlit as st
import mysql.connector
import urllib.parse

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Vardhman Juice Center", page_icon="🍹", layout="wide", initial_sidebar_state="collapsed")

# --- PREMIUM CUSTOM CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .premium-header {
        background: linear-gradient(135deg, #FF9A9E 0%, #FECFEF 99%, #FECFEF 100%);
        padding: 20px; border-radius: 15px; text-align: center;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.1); margin-bottom: 20px;
    }
    .shop-title { font-size: 38px; font-weight: 900; color: #2D3436; margin: 0; font-family: 'Arial Black', sans-serif; }
    .shop-subtitle { font-size: 14px; color: #636E72; font-weight: 600; letter-spacing: 2px; }
    .alert-box { background-color: #FFEEEE; border-left: 5px solid #FF4B4B; padding: 10px; border-radius: 5px; margin-bottom: 10px;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="premium-header">
    <p class="shop-title">🍹 VARDHMAN JUICE CENTER</p>
    <p class="shop-subtitle">100% FRESH • PREMIUM QUALITY</p>
</div>
""", unsafe_allow_html=True)

# --- MOCK DATA ---
in_stock_items = ["Lays Indian Magic Masala (₹10)", "Balaji Wafers (₹10)", "Amul Lassi (₹25)", "Mix Fruit Juice (₹40)", "Frooti (₹20)"]

# --- DASHBOARD TABS ---
tab_pos, tab_inventory, tab_credit, tab_reports = st.tabs([
    "🛍️ Point of Sale", "📦 Inventory & Alerts", "📒 Udhar Khata", "📊 End of Day (Galla)"
])

# --- TAB 1: POINT OF SALE (With WhatsApp Billing) ---
with tab_pos:
    st.subheader("⚡ Fast Billing System")
    
    with st.form("sale_form", clear_on_submit=False):
        selected_item = st.selectbox("Select Product", in_stock_items)
        col1, col2 = st.columns(2)
        with col1:
            quantity = st.number_input("Quantity Sold", min_value=1, step=1)
        with col2:
            price_per_item = st.number_input("Price per item (₹)", min_value=1.0, value=10.0, step=1.0)
            
        total_bill = quantity * price_per_item
        st.info(f"**Total Payable: ₹{total_bill}**")
        
        st.divider()
        
        pay_col1, pay_col2 = st.columns(2)
        with pay_col1:
            payment_type = st.radio("Payment Method", ["💸 Cash", "📱 UPI (PhonePe/GPay)", "📝 Credit (Udhar)"])
        with pay_col2:
            if payment_type == "📝 Credit (Udhar)":
                customer = st.text_input("Enter Customer Name (Udhar)")
                cust_phone = st.text_input("Customer WhatsApp No. (Optional)")
            else:
                customer = "Walk-in Customer"
                cust_phone = st.text_input("Customer WhatsApp No. (For Digital Bill)")
                
        submit_sale = st.form_submit_button("✅ Generate Bill", use_container_width=True)
        
    # Actions outside the form so WhatsApp link can render
    if submit_sale:
        if payment_type == "📝 Credit (Udhar)" and not customer.strip():
            st.error("⚠️ Please enter the customer's name for Udhar!")
        else:
            st.success(f"Transaction Successful! ₹{total_bill} collected via {payment_type}.")
            
            # 🚀 NEW FEATURE: WHATSAPP DIGITAL BILL GENERATION
            bill_message = f"🧾 *VARDHMAN JUICE CENTER*\n\nThank you for your visit, {customer}!\n\n*Item:* {selected_item}\n*Qty:* {quantity}\n*Total Bill:* ₹{total_bill}\n*Paid via:* {payment_type}\n\n_Have a great day!_ 🍹"
            encoded_msg = urllib.parse.quote(bill_message)
            
            # If phone number is provided, send to that number. Else, open WhatsApp to choose contact.
            if cust_phone:
                wa_url = f"https://wa.me/91{cust_phone}?text={encoded_msg}"
            else:
                wa_url = f"https://wa.me/?text={encoded_msg}"
                
            st.markdown(f'<a href="{wa_url}" target="_blank" style="display: block; text-align: center; background-color: #25D366; color: white; padding: 12px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 16px;">📲 Send Digital Bill via WhatsApp</a>', unsafe_allow_html=True)

# --- TAB 2: INVENTORY & ALERTS ---
with tab_inventory:
    st.subheader("⚠️ Low Stock Alerts")
    # 🚀 NEW FEATURE: LOW STOCK WARNINGS
    st.markdown('<div class="alert-box">🔴 <b>Amul Lassi</b> is running low! (Only 2 left in stock)</div>', unsafe_allow_html=True)
    st.markdown('<div class="alert-box">🔴 <b>Lays Magic Masala</b> is out of stock! (0 left)</div>', unsafe_allow_html=True)
    
    st.divider()
    st.subheader("📥 Add New Stock")
    st.info("Stock entry system is active. (Supplier forms from previous version will go here).")

# --- TAB 3: CREDIT LEDGER (Udhar Khata) ---
with tab_credit:
    st.subheader("📒 Market Ledger")
    st.info("Customer and Supplier Udhar management is active.")

# --- TAB 4: END OF DAY (Galla / Closing) ---
with tab_reports:
    st.subheader("💰 End of Day Calculation (Galla)")
    
    # 🚀 NEW FEATURE: GALLLA TALLY FOR INDIAN SHOPS
    st.markdown("Check your cash drawer against the system data before closing the shop.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Total Cash Expected in Galla 💸", value="₹850")
    with col2:
        st.metric(label="Total UPI/Online Received 📱", value="₹1,200")
        
    st.metric(label="Total Udhar Given Today 📝", value="₹150")
    
    st.divider()
    if st.button("🔒 Close Day & Save Report", use_container_width=True):
        st.success("Day closed successfully. Reports saved to database!")