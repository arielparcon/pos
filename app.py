import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="POS Template Converter", page_icon="📊", layout="centered")

st.title("POS Template Converter")

uploaded_file = st.file_uploader("Choose your CSV file", type=["csv"])

if uploaded_file is not None:
    st.success("File uploaded successfully!")

    try:
        df = pd.read_csv(uploaded_file)

        df.columns = df.columns.str.strip()
        
        required_cols = ['Item Name', 'Category', 'Status', 'Rm. Service-WI Rate']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            st.error(f"Missing required columns in your file: {', '.join(missing_cols)}")
            st.stop()

        df_active = df[df['Status'].astype(str).str.strip().str.lower() == 'active'].copy()
        
        if df_active.empty:
            st.warning("No 'active' items found in the uploaded file. Please check your 'Status' column.")
            st.stop()
            
        st.info(f"Found **{len(df_active)}** active items ready for conversion.")

        df_active['Product Id'] = ['RMS' + str(i).zfill(3) for i in range(1, len(df_active) + 1)]

        new_df = pd.DataFrame()
        new_df['Featured Product'] = 'N'
        new_df['Pos Point Short Name'] = ''
        new_df['Pos Product Name'] = df_active['Item Name']
        new_df['Product Id'] = df_active['Product Id']
        new_df['Description'] = ''
        new_df['Pos Categories'] = df_active['Category']
        new_df['Taxes Short Name'] = 'VAT'
        new_df[' Pos Attributes'] = 
        new_df['Price'] = df_active['Rm. Service-WI Rate']
        new_df['NC value(%)'] = ''
        new_df['Unit Short Name'] = 'Unit'
        new_df['Kitchen Code'] = 'KIT'
        new_df['Status'] = 'A'
 
        csv_data = new_df.to_csv(index=False).encode('utf-8')
        
        st.subheader("Preview of Converted Data")
        st.dataframe(new_df.head(10))
        
        if len(new_df) > 10:
            st.caption(f"... and {len(new_df) - 10} more rows.")

        st.download_button(
            label="⬇Download Converted CSV",
            data=csv_data,
            file_name="HLX_Converted_Template.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")