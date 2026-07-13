import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="POS Template Converter", layout="centered")

st.title("POS Template Converter")
st.markdown("""
INSTRUCTIONS:
1. Export the food items of the branch from POSIST first.
2. Import the exported CSV file here and click on the "Download Converted CSV" button to get the HLX pos template.
3. Use the downloaded CSV file to migrate the active food items into HLX.
""")

def calculate_net_price(val):
    if pd.isna(val) or str(val).strip() == '':
        return '0' 
    try:
        net_amount = float(val) / 1.12
        return f"{net_amount:.6f}"
    except (ValueError, TypeError):
        return '0'

uploaded_file = st.file_uploader("Choose your CSV file", type=["csv"])

if uploaded_file is not None:
    st.success("File uploaded successfully!")
  
    uploaded_filename = uploaded_file.name
    filename_without_ext = os.path.splitext(uploaded_filename)[0]
 
    if '_' in filename_without_ext:
        prefix = filename_without_ext.split('_')[0]
    else:
        prefix = filename_without_ext
    
    output_filename = f"{prefix}_pos_template.csv"

    try:
        df_temp = pd.read_csv(uploaded_file, nrows=5)
        first_cell = str(df_temp.iloc[0, 0]).lower().strip()
        has_headers = first_cell in ['item name', 'item', 'name', 'product', 'product name']

        uploaded_file.seek(0)
        
        if has_headers:
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file, header=None)

        num_cols = df.shape[1]

        if num_cols < 15:
            st.error(f"Your file must have at least 15 columns. Currently has: {num_cols}")
            st.stop()

        df_named = pd.DataFrame({
            'Item Name': df.iloc[:, 1],     
            'Category': df.iloc[:, 5],     
            'Status': df.iloc[:, 14],      
            'Price': df.iloc[:, 4]        
        })

        df_active = df_named[df_named['Status'].astype(str).str.strip().str.lower() == 'active'].copy()
        
        if df_active.empty:
            st.warning("No 'active' items found in the uploaded file. Please check the 15th column (Status).")
            st.stop()
            
        st.info(f"Found **{len(df_active)}** active items ready for conversion.")
        st.caption(f"Output file will be: **{output_filename}**")

        prices = [calculate_net_price(row['Price']) for _, row in df_active.iterrows()]

        df_active['Item Name'] = df_active['Item Name'].fillna('').astype(str).str.strip()
        df_active['Category'] = df_active['Category'].fillna('').astype(str).str.strip()
        
        is_free_item = df_active['Item Name'].str.lower().str.startswith('free')

        df_active.loc[is_free_item, 'Category'] = 'Free'

        product_ids = ['RMS' + str(i).zfill(3) for i in range(1, len(df_active) + 1)]

        featured_products = ['N'] * len(df_active)
        pos_point_names = ['RMS'] * len(df_active)
        pos_product_names = df_active['Item Name'].tolist()
        descriptions = [''] * len(df_active)
        pos_categories = df_active['Category'].tolist()
        taxes_short_names = ['VAT'] * len(df_active)
        pos_attributes = [''] * len(df_active)
        nc_values = [''] * len(df_active)
        unit_short_names = ['Unit'] * len(df_active)
        kitchen_codes = ['KIT'] * len(df_active)
        statuses = ['A'] * len(df_active)

        new_df = pd.DataFrame({
            'Featured Product': featured_products,
            'Pos Point Short Name': pos_point_names,
            'Pos Product Name': pos_product_names,
            'Product Id': product_ids,
            'Description': descriptions,
            'Pos Categories': pos_categories,
            'Taxes Short Name': taxes_short_names,
            'Pos Attributes': pos_attributes,
            'Price': prices,
            'NC value(%)': nc_values,
            'Unit Short Name': unit_short_names,
            'Kitchen Code': kitchen_codes,
            'Status': statuses
        })

        csv_data = new_df.to_csv(index=False).encode('utf-8')
        
        st.subheader("Preview of Converted Data")
        st.dataframe(new_df.head(10))
        
        if len(new_df) > 10:
            st.caption(f"... and {len(new_df) - 10} more rows.")

        st.download_button(
            label="⬇️ Download Converted CSV",
            data=csv_data,
            file_name=output_filename,
            mime="text/csv",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
        st.exception(e)
