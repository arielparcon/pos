import pandas as pd

def convert_pos_template(input_file_path, output_file_path):
    try:
        df = pd.read_csv(input_file_path)
        df_active = df[df['Status'].astype(str).str.strip().str.lower() == 'active'].copy()
        
        if df_active.empty:
            print("No 'active' items found in the uploaded file.")
            return
        df_active['Product Id'] = ['RMS' + str(i).zfill(3) for i in range(1, len(df_active) + 1)]

        new_df = pd.DataFrame()
        new_df['Featured Product'] = 'N'
        new_df['Pos Point Short Name'] = ''
        new_df['Pos Product Name'] = df_active['Item Name']
        new_df['Product Id'] = df_active['Product Id']
        new_df['Description'] = ''
        new_df['Pos Categories'] = df_active['Category']
        new_df['Taxes Short Name'] = 'VAT'
        new_df['Pos Attributes'] = ''
        new_df['Price'] = df_active['Rm. Service-WI Rate']
        new_df['NC value(%)'] = ''
        new_df['Unit Short Name'] = 'Unit'
        new_df['Kitchen Code'] = 'KIT'
        new_df['Status'] = 'A'

        new_df.to_csv(output_file_path, index=False)
        print(f"Conversion successful! {len(new_df)} active items processed.")
        print(f"Saved to: {output_file_path}")
        
    except KeyError as e:
        print(f"Error: Missing required column in your uploaded file: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
