
import pandas as pd
from app.database_handler import DatabaseHandler
import json
import numpy as np

def test_serialization():
    handler = DatabaseHandler()
    handler.connect("sqlite:///data/sample_store.db")
    
    # Query that returns dates and numbers
    success, df, msg = handler.execute_query("SELECT * FROM customers")
    
    if hasattr(df, 'to_dict'):
        data = df.to_dict('records')
        print("Data sample:", data[0])
        
        # Test JSON dump
        try:
            json_str = json.dumps(data, default=str) # Flask uses something similar but more robust?
            print("\nJSON serialization successful!")
            # Check for NaN
            if 'NaN' in json_str:
                print("WARNING: NaN found in JSON string")
        except Exception as e:
            print(f"\nJSON serialization failed: {e}")

        # Check types
        print("\nTypes in first row:")
        for k, v in data[0].items():
            print(f"{k}: {type(v)}")

if __name__ == "__main__":
    test_serialization()
