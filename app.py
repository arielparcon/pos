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
  
    uploaded_filename = uploaded_file.name
    filename_without_ext = os.path.splitext(uploaded_filename)[0]
 
    if '_' in filename_without_ext:
        prefix = filename_without_ext.split('_')[0]
    else:
        prefix = filename_without_ext
    
    output_filename_rms = f"{prefix}_RoomService_pos_template.csv"
    output_filename_misc = f"{prefix}_Miscellaneous_pos_template.csv"

    try:
        df = pd.read_csv(uploaded_file)

        df.columns = df.columns.str.strip()

        with st.expander("(for debugging)"):
            st.write("Column names found in your file:")
            st.write(list(df.columns))

        price_col_rms = None
        for col in df.columns:
            if col.lower() in ['rm. service - wi rate', 'room service - wi rate', 'room service wi rate', 'room service rate']:
                price_col_rms = col
                break
        
        if price_col_rms is None:
            st.error("❌ Could not find Room Service price column (Rm. Service - WI Rate or similar).")
            st.write("Available columns:", list(df.columns))
            st.stop()

        price_col_misc = None
        for col in df.columns:
            if col.lower() in ['misc - wi rate', 'miscellaneous - wi rate', 'misc wi rate', 'miscellaneous rate']:
                price_col_misc = col
                break
        
        if price_col_misc is None:
            st.error("❌ Could not find Miscellaneous price column (Misc - WI Rate or similar).")
            st.write("Available columns:", list(df.columns))
            st.stop()

        status_col_rms = None
        for col in df.columns:
            if col.lower() in ['rm. service - wi status', 'room service - wi status', 'room service wi status', 'room service status']:
                status_col_rms = col
                break
        
        if status_col_rms is None:
            st.error("❌ Could not find Room Service status column (Rm. Service - WI Status or similar).")
            st.write("Available columns:", list(df.columns))
            st.stop()

        status_col_misc = None
        for col in df.columns:
            if col.lower() in ['misc - wi status', 'miscellaneous - wi status', 'misc wi status', 'miscellaneous status']:
                status_col_misc = col
                break
        
        if status_col_misc is None:
            st.error("❌ Could not find Miscellaneous status column (Misc - WI Status or similar).")
            st.write("Available columns:", list(df.columns))
            st.stop()

        item_name_col = None
        for col in df.columns:
            if 'item name' in col.lower() or 'itemnam' in col.lower() or col.lower() == 'item':
                item_name_col = col
                break
        
        if item_name_col is None:
            item_name_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

        category_col = None
        for col in df.columns:
            if 'category' in col.lower():
                category_col = col
                break
        
        if category_col is None:
            category_col = df.columns[5] if len(df.columns) > 5 else df.columns[0]

        df_processed = pd.DataFrame({
            'Item Name': df[item_name_col].fillna('').astype(str).str.strip(),
            'Category': df[category_col].fillna('').astype(str).str.strip(),
            'Price_RMS': df[price_col_rms],
            'Price_Misc': df[price_col_misc],
            'Status_RMS': df[status_col_rms].astype(str).str.strip().str.lower(),
            'Status_Misc': df[status_col_misc].astype(str).str.strip().str.lower()
        })

        df_processed.loc[df_processed['Item Name'].str.contains('extra', case=False, na=False), 'Category'] = 'Extra'

        misc_categories = ['miscellaneous', 'free', 'extra']
        df_processed['Is_Misc'] = df_processed['Category'].str.lower().str.strip().isin(misc_categories)

        df_rms = df_processed[~df_processed['Is_Misc']].copy()
        df_rms = df_rms[df_rms['Status_RMS'] == 'active'].copy()

        df_misc = df_processed[df_processed['Is_Misc']].copy()
        df_misc = df_misc[df_misc['Status_Misc'] == 'active'].copy()

        def assign_final_price(row, is_misc):
            if is_misc:
                price_val = row['Price_Misc']
            else:
                price_val = row['Price_RMS']
            
            if pd.isna(price_val) or str(price_val).strip() == '':
                return '0'
            try:
                return f"{float(price_val) / 1.12:.6f}"
            except (ValueError, TypeError):
                return '0'

        df_rms['Final_Price'] = df_rms.apply(lambda row: assign_final_price(row, is_misc=False), axis=1)
        df_misc['Final_Price'] = df_misc.apply(lambda row: assign_final_price(row, is_misc=True), axis=1)

        st.success(f"✅ Processed: **{len(df_rms)}** Room Service items, **{len(df_misc)}** Miscellaneous items")

        df_rms_pos = generate_pos_template(df_rms, point_name='RMS')
        df_misc_pos = generate_pos_template(df_misc, point_name='MISC')

        tab1, tab2 = st.tabs(["🏨 Room Service Preview", "🧾 Miscellaneous Preview"])

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
                st.warning("No items matched the criteria for Miscellaneous.")
        
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
        st.exception(e)
