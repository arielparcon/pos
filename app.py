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
    
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip()

        outlets = {
            'Room Service': 'RMSWI',
            'All Day Dining': 'ALLDAY',
            'Breakfast Buffet Set': 'BRKBUFF',
            'France': 'FRANC',
            'Miscellaneous': 'MISCWI',
            'Lobby': 'LOBBY',
            'Germany': 'GERM',
            'Massage': 'MSSG',
            'KTV': 'KV'
        }

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

        # Find Rate and Status columns for each outlet
        outlet_cols = {}
        for outlet_name in outlets.keys():
            rate_col = None
            status_col = None
            outlet_lower = outlet_name.lower()
            
            for col in df.columns:
                col_lower = col.lower()
                if outlet_lower in col_lower:
                    if 'rate' in col_lower:
                        rate_col = col
                    elif 'status' in col_lower:
                        status_col = col

            if not rate_col:
                for col in df.columns:
                    if col.lower() == outlet_lower:
                        rate_col = col
                        break
                        
            outlet_cols[outlet_name] = {'rate': rate_col, 'status': status_col}

        missing_cols = []
        for outlet_name, cols in outlet_cols.items():
            if not cols['rate']:
                missing_cols.append(f"{outlet_name} Rate")
            if not cols['status']:
                missing_cols.append(f"{outlet_name} Status")
                
        if missing_cols:
            st.error(f"❌ Could not find the following columns: {', '.join(missing_cols)}")
            st.write("Available columns:", list(df.columns))
            st.stop()

        df_processed = pd.DataFrame({
            'Item Name': df[item_name_col].fillna('').astype(str).str.strip(),
            'Category': df[category_col].fillna('').astype(str).str.strip(),
        })

        df_processed.loc[df_processed['Item Name'].str.contains('extra', case=False, na=False), 'Category'] = 'Extra'
        df_processed.loc[df_processed['Item Name'].str.lower().str.startswith('free'), 'Category'] = 'Free'

        df_processed['Is_Free_Or_Extra'] = df_processed['Category'].str.lower().str.strip().isin(['free', 'extra'])

        outlet_dfs = {}
        for outlet_name in outlets.keys():
            rate_col = outlet_cols[outlet_name]['rate']
            status_col = outlet_cols[outlet_name]['status']
            
            df_outlet = df_processed.copy()
            df_outlet['Status'] = df[status_col].astype(str).str.strip().str.lower()
            df_outlet['Price'] = df[rate_col]

            df_outlet = df_outlet[df_outlet['Status'] == 'active'].copy()

            if outlet_name != 'Miscellaneous':
                df_outlet = df_outlet[~df_outlet['Is_Free_Or_Extra']].copy()

            df_outlet['Final_Price'] = df_outlet['Price'].apply(calculate_net_price)
            
            outlet_dfs[outlet_name] = df_outlet

        total_items = len(df_processed)
        free_extra_count = df_processed['Is_Free_Or_Extra'].sum()
        st.info(f"📊 Total items: **{total_items}** | Free/Extra items: **{free_extra_count}** (will only appear in Miscellaneous)")

        st.success(f"✅ Processed items for {len(outlet_dfs)} outlets.")

        active_outlets = [name for name, df_out in outlet_dfs.items() if not df_out.empty]
        
        if not active_outlets:
            st.warning("No active items found for any of the requested outlets.")
        else:
            tabs = st.tabs([f"{outlet} Preview" for outlet in active_outlets])

            for i, outlet_name in enumerate(active_outlets):
                with tabs[i]:
                    short_name = outlets[outlet_name]
                    df_outlet = outlet_dfs[outlet_name]
                    df_pos = generate_pos_template(df_outlet, point_name=short_name)
                    
                    if df_pos is not None and not df_pos.empty:
                        st.dataframe(df_pos.head(10))
                        if len(df_pos) > 10:
                            st.caption(f"... and {len(df_pos) - 10} more rows.")
 
                        category_counts = df_outlet['Category'].value_counts()
                        st.caption(f"Categories in this outlet: {dict(category_counts)}")

                        file_name = f"{prefix}_{outlet_name.replace(' ', '')}_pos_template.csv"
                        csv_data = df_pos.to_csv(index=False).encode('utf-8')
                        
                        st.download_button(
                            label=f"⬇️ Download {outlet_name} CSV",
                            data=csv_data,
                            file_name=file_name,
                            mime="text/csv",
                            use_container_width=True
                        )
                    else:
                        st.warning(f"No items matched the criteria for {outlet_name}.")
        
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
        st.exception(e)
