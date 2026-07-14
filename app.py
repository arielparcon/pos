import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="POS Template Converter", layout="centered")

st.title("POS Template Converter")
st.markdown("""
INSTRUCTIONS:
1. Export the food items of the branch from POSIST first.
2. Import the exported CSV file here and click on the "Download Converted CSV" buttons to get the HLX pos templates.
3. Use the downloaded CSV files to migrate the active food items into HLX.
""")

def calculate_net_price(val):
    if pd.isna(val) or str(val).strip() == '':
        return '0' 
    try:
        net_amount = float(val) / 1.12
        return f"{net_amount:.6f}"
    except (ValueError, TypeError):
        return '0'

def generate_pos_template(df_subset, point_name):
    """Helper function to generate the formatted POS dataframe for a specific outlet."""
    if df_subset.empty:
        return None

    prices = df_subset['Final_Price'].tolist()
    product_ids = [point_name + str(i).zfill(3) for i in range(1, len(df_subset) + 1)]
    
    return pd.DataFrame({
        'Featured Product': ['N'] * len(df_subset),
        'Pos Point Short Name': [point_name] * len(df_subset),
        'Pos Product Name': df_subset['Item Name'].tolist(),
        'Product Id': product_ids,
        'Description': [''] * len(df_subset),
        'Pos Categories': df_subset['Category'].tolist(),
        'Taxes Short Name': ['VAT'] * len(df_subset),
        'Pos Attributes': [''] * len(df_subset),
        'Price': prices,
        'NC value(%)': [''] * len(df_subset),
        'Unit Short Name': ['Unit'] * len(df_subset),
        'Kitchen Code': ['KIT'] * len(df_subset),
        'Status': ['A'] * len(df_subset)
    })

uploaded_file = st.file_uploader("Choose your CSV file", type=["csv"])

if uploaded_file is not None:
    st.success("File uploaded successfully!")
  
    uploaded_filename = uploaded_file.name
    filename_without_ext = os.path.splitext(uploaded_filename)[0]
 
    if '_' in filename_without_ext:
        prefix = filename_without_ext.split('_')[0]
    else:
        prefix = filename_without_ext
    
    output_filename_rms = f"{prefix}_RoomService_pos_template.csv"
    output_filename_misc = f"{prefix}_Miscellaneous_pos_template.csv"

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

        if num_cols < 29:
            st.error(f"Your file must have at least 29 columns. Currently has: {num_cols}")
            st.stop()

        df_named = pd.DataFrame({
            'Item Name': df.iloc[:, 1],   
            'Category': df.iloc[:, 5],    
            'Status': df.iloc[:, 14],     
            'Price_5': df.iloc[:, 4],   
            'Price_17': df.iloc[:, 16],    
            'Price_29': df.iloc[:, 28]     
        })

        df_active = df_named[df_named['Status'].astype(str).str.strip().str.lower() == 'active'].copy()
        
        if df_active.empty:
            st.warning("No 'active' items found in the uploaded file. Please check the 15th column (Status).")
            st.stop()
            
        st.info(f"Found **{len(df_active)}** total active items ready for conversion.")

        df_active['Item Name'] = df_active['Item Name'].fillna('').astype(str).str.strip()
        df_active['Category'] = df_active['Category'].fillna('').astype(str).str.strip()

        df_active.loc[df_active['Item Name'].str.contains('extra', case=False, na=False), 'Category'] = 'Extra'

        df_active.loc[df_active['Item Name'].str.lower().str.startswith('free'), 'Category'] = 'Free'

        misc_categories = ['miscellaneous', 'free', 'extra']
        is_misc = df_active['Category'].str.lower().str.strip().isin(misc_categories)
        
        df_misc = df_active[is_misc].copy()
        df_rms = df_active[~is_misc].copy()

        final_prices = []
        for _, row in df_active.iterrows():
            cat = str(row['Category']).lower().strip()
            p5 = row['Price_5']
            p17 = row['Price_17']
            p29 = row['Price_29']

            if cat in misc_categories:
                is_empty_29 = pd.isna(p29) or str(p29).strip() == ''
                if not is_empty_29:
                    final_prices.append(calculate_net_price(p29))
                else:
                    final_prices.append(calculate_net_price(p17))
            else:
                is_empty_17 = pd.isna(p17) or str(p17).strip() == ''
                if not is_empty_17:
                    final_prices.append(calculate_net_price(p17))
                else:
                    final_prices.append(calculate_net_price(p5))

        df_active['Final_Price'] = final_prices

        df_misc = df_active[is_misc].copy()
        df_rms = df_active[~is_misc].copy()

        st.success(f"Split successful: **{len(df_rms)}** items for Room Service, **{len(df_misc)}** items for Miscellaneous.")

        df_rms_pos = generate_pos_template(df_rms, point_name='RMS')
        df_misc_pos = generate_pos_template(df_misc, point_name='MISC')

        tab1, tab2 = st.tabs(["Room Service Preview", "Miscellaneous Preview"])

        with tab1:
            if df_rms_pos is not None and not df_rms_pos.empty:
                st.dataframe(df_rms_pos.head(10))
                if len(df_rms_pos) > 10:
                    st.caption(f"... and {len(df_rms_pos) - 10} more rows.")
                
                csv_data_rms = df_rms_pos.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="⬇️ Download Room Service CSV",
                    data=csv_data_rms,
                    file_name=output_filename_rms,
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("No items matched the criteria for Room Service.")

        with tab2:
            if df_misc_pos is not None and not df_misc_pos.empty:
                st.dataframe(df_misc_pos.head(10))
                if len(df_misc_pos) > 10:
                    st.caption(f"... and {len(df_misc_pos) - 10} more rows.")
                
                csv_data_misc = df_misc_pos.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="⬇️ Download Miscellaneous CSV",
                    data=csv_data_misc,
                    file_name=output_filename_misc,
                    mime="text/csv",
                    use_container_width=True,
                    type="secondary"
                )
            else:
                st.warning("No items matched the criteria for Miscellaneous (Free, Extra, or Miscellaneous).")
        
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
        st.exception(e)
