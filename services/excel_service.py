import pandas as pd
import re
import numpy as np

def clean_text(val):
    """
    Aggressively cleans text:
    - Removes newlines/tabs
    - Collapses multiple spaces
    - Trims whitespace
    - Handles None/NaN
    """
    if val is None or pd.isna(val):
        return ""
    
    # Convert to string
    s = str(val)
    
    # Remove control characters and normalize spaces
    s = re.sub(r'[\r\n\t]+', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    
    return s.strip()

def get_smart_df(path, sheet=None):
    """
    Smart Data Repair Engine
    1. Detects true header row via scoring
    2. Normalizes column headers
    3. Cleans entire dataset
    """
    raw_df = None
    try:
        # Default to first sheet if not specified
        if sheet is None:
            sheet = 0

        # 1. Load Data with Maximum Tolerance
        if path.lower().endswith('.csv'):
            for enc in ['utf-8-sig', 'cp874', 'tis-620', 'utf-8', 'latin1']:
                try:
                    raw_df = pd.read_csv(path, header=None, encoding=enc, skip_blank_lines=False)
                    break
                except:
                    continue
        elif path.lower().endswith('.xls'):
            raw_df = pd.read_excel(path, sheet_name=sheet, header=None, engine='xlrd')
        else:
            raw_df = pd.read_excel(path, sheet_name=sheet, header=None, engine='openpyxl')

        if raw_df is None or raw_df.empty:
            return pd.DataFrame()

        # 2. Smart Header Detection
        # Scan first 25 rows to find the most "header-like" row
        sample = raw_df.head(25)
        best_idx = 0
        max_score = -1

        for i in range(len(sample)):
            row = sample.iloc[i]
            
            # Score Components:
            # - Filled Count (Reward)
            # - Unique Values (Reward: Headers usually unique)
            # - String Type (Reward: Headers usually strings)
            
            non_nulls = row.dropna()
            filled_count = len(non_nulls)
            
            if filled_count == 0:
                continue

            # Check uniqueness
            unique_count = non_nulls.nunique()
            
            # Check for string content
            str_count = sum(1 for x in non_nulls if isinstance(x, str))
            
            # Calculate Score
            # Weight filled count heavily, but boost if unique and strings
            score = (filled_count * 2) + (unique_count * 1.5) + (str_count * 1)
            
            if score > max_score:
                max_score = score
                best_idx = i

        # 3. Apply Header & Slice
        df = raw_df.iloc[best_idx:].reset_index(drop=True)
        
        # 4. Normalize Columns
        clean_cols = []
        counts = {}
        
        for c in df.iloc[0]:
            clean_c = clean_text(c)
            
            # Handle empty or default names
            if not clean_c or "Unnamed" in clean_c or clean_c.lower() == "nan":
                clean_c = "Field"
            
            # Handle duplicates (e.g., "Date", "Date" -> "Date", "Date_2")
            if clean_c in counts:
                counts[clean_c] += 1
                final_name = f"{clean_c}_{counts[clean_c]}"
            else:
                counts[clean_c] = 1
                final_name = clean_c
                
            clean_cols.append(final_name)

        df.columns = clean_cols
        df = df.iloc[1:] # Drop the header row itself

        # 5. Aggressive Data Cleaning
        # - Drop completely empty rows
        # - Fill NaN with ""
        # - Trim all cells
        
        df = df.replace(r'^\s*$', np.nan, regex=True) # treat spaces as NaN
        df = df.dropna(how='all') # drop completely empty rows
        df = df.fillna("") # fill remaining NaNs
        
        # Apply cleaner to every cell (vectorized map is faster, but simple applymap is safer for mixed types)
        try:
            df = df.map(clean_text)
        except AttributeError:
            df = df.applymap(clean_text) # older pandas

        return df

    except Exception as e:
        print(f"❌ Smart Repair Failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Failsafe: Try standard read if smart repair crashes
        try:
            print("⚠️ Attempting Failsafe Read...")
            if path.lower().endswith('.csv'):
                return pd.read_csv(path)
            else:
                return pd.read_excel(path)
        except Exception as e2:
            print(f"❌ Failsafe Failed: {e2}")
            return pd.DataFrame()
