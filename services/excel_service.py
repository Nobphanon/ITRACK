import pandas as pd
import re

def get_smart_df(path, sheet=None):
    """
    Reads an Excel or CSV file and intelligently identifies the header row.
    Auto-cleans column names and handles encoding for CSVs.
    """
    raw_df = None
    try:
        if path.lower().endswith('.csv'):
            for enc in ['utf-8-sig', 'tis-620', 'cp874', 'utf-8']:
                try:
                    raw_df = pd.read_csv(path, header=None, encoding=enc, skip_blank_lines=True)
                    break
                except:
                    continue
        elif path.lower().endswith('.xls'):
            # Legacy Excel support via xlrd
            raw_df = pd.read_excel(path, sheet_name=sheet, header=None, engine='xlrd')
        else:
            # Modern Excel support via openpyxl (default)
            raw_df = pd.read_excel(path, sheet_name=sheet, header=None, engine='openpyxl')

        if raw_df is None or raw_df.empty:
            return pd.DataFrame()

        # Find the header row (row with most non-null values)
        sample = raw_df.head(20)
        header_idx = sample.count(axis=1).idxmax()
        if header_idx == 0:
            for i in range(len(sample)):
                filled = sample.iloc[i].notna().sum()
                if filled >= len(sample.columns) * 0.5:
                    header_idx = i
                    break
        
        df = raw_df.iloc[header_idx:].reset_index(drop=True)

        # Clean column names
        clean_cols = []
        for c in df.iloc[0]:
            c_str = re.sub(r'\s+', ' ', str(c)).strip()
            if not c_str or "Unnamed" in c_str or c_str.lower() == "nan":
                clean_cols.append(f"Field_{len(clean_cols)+1}")
            else:
                clean_cols.append(c_str)

        df.columns = clean_cols
        df = df.iloc[1:]
        
        # Robust dropna: Drop rows where all elements are null or empty strings
        df = df.replace(r'^\s*$', pd.NA, regex=True)
        df = df.dropna(how='all')
        df = df.fillna("")

        # Normalize data
        try:
            df = df.map(lambda x: str(x).strip() if x is not None else "")
        except AttributeError:
            df = df.applymap(lambda x: str(x).strip() if x is not None else "")

        # Clean whitespace in headers
        df.columns = (
            df.columns.astype(str)
            .str.replace('\n', ' ')
            .str.replace('\r', ' ')
            .str.replace(r'\s+', ' ', regex=True)
            .str.strip()
        )

        return df

    except Exception as e:
        print(f"Smart Reader Error: {e}")
        return pd.DataFrame()
