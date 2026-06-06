import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="POS Template Converter", page_icon="📊", layout="centered")

st.title("POSIST to HLX Template Converter")
st.markdown("""
INSTRUCTIONS:
1. Export the food items of the branch from the POSIST first.
2. Import the exported CSV file here and click on the "Download Converted CSV" button to get the HLX pos template.
3. Use the downloaded CSV file to migrate the active food items into HLX.
""")

uploaded_file = st.file_uploader("Please upload your POSist CSV file below.", type=["csv"])

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
            df.columns = df.columns.str.strip()
            
            required_cols = ['Item Name', 'Category', 'Status']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"Missing required columns in your file: {', '.join(missing_cols)}")
                st.stop()
       
            df_named = pd.DataFrame({
                'Item Name': df['Item Name'],
                'Category': df['Category'],
                'Status': df['Status'],
                'Price_Value': df.iloc[:, 4]
            })
        else:

            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, header=None)

            if df.shape[1] < 5:
                st.error(f"Your file must have at least 5 columns. Currently has: {df.shape[1]}")
                st.stop()

            df_named = pd.DataFrame({
                'Item Name': df.iloc[:, 1],  
                'Category': df.iloc[:, 2],   
                'Status': df.iloc[:, 3],     
                'Price_Value': df.iloc[:, 4]  
            })

        df_active = df_named[df_named['Status'].astype(str).str.strip().str.lower() == 'active'].copy()
        
        if df_active.empty:
            st.warning("No 'active' items found in the uploaded file. Please check your 'Status' column.")
            st.stop()
            
        st.info(f"Found **{len(df_active)}** active items ready for conversion.")

        product_ids = ['RMS' + str(i).zfill(3) for i in range(1, len(df_active) + 1)]
 
        featured_products = ['N'] * len(df_active)
        pos_point_names = ['RMS'] * len(df_active)
        pos_product_names = df_active['Item Name'].fillna('').tolist()
        descriptions = [''] * len(df_active)
        pos_categories = df_active['Category'].fillna('').tolist()
        taxes_short_names = ['VAT'] * len(df_active)
        pos_attributes = [''] * len(df_active)
        prices = df_active['Price_Value'].fillna('').tolist()
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
            ' Pos Attributes': pos_attributes,
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
            label="Download Converted CSV",
            data=csv_data,
            file_name=output_filename,
            mime="text/csv",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
        st.exception(e) 