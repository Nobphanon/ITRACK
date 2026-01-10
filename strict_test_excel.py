import pandas as pd
import numpy as np
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    from services.excel_service import get_smart_df
    print("✅ Successfully imported get_smart_df")
except Exception as e:
    print(f"❌ ImportError: {e}")
    sys.exit(1)

# Create a dummy excel file
df = pd.DataFrame({
    'Header A': [1, 2, 3],
    'Header B': ['x', 'y', 'z']
})

test_path = "test_smart_excel.xlsx"
df.to_excel(test_path, index=False)

try:
    print(f"Testing with {test_path}...")
    result_df = get_smart_df(test_path)
    if not result_df.empty:
        print("✅ Success! returned DataFrame:")
        print(result_df)
    else:
        print("❌ Failed! returned empty DataFrame")
except Exception as e:
    print(f"❌ Execution Error: {e}")
finally:
    if os.path.exists(test_path):
        os.remove(test_path)
