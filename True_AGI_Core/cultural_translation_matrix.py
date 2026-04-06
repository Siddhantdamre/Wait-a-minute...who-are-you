import pandas as pd
import torch
import os

def load_cultural_prior(country_name, dim=4, csv_filename="hofstede_country_scores.csv"):
    """
    Loads Hofstede dimensions for a given country from the CSV dataset.
    Normalizes the scores (usually 0-100) to a tensor suitable for neural network initialization.
    Assumes dimensions correspond to PDI, IDV, MAS, UAI (if dim=4).
    """
    # Find CSV in parent directory
    csv_path = os.path.join(os.path.dirname(__file__), "..", csv_filename)
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Could not find {csv_path}")

    # Load dataframe, drop rows with missing values
    df = pd.read_csv(csv_path)
    
    # Capitalize the search to be safe, but data looks to be sentence case
    country_row = df[df['country'].str.lower() == country_name.lower()]
    
    if country_row.empty:
        raise ValueError(f"Country '{country_name}' not found in dataset.")
        
    scores = country_row.iloc[0][['pdi', 'idv', 'mas', 'uai']].values
    
    # Handle possible empty/nan strings by coercing to numeric
    scores = pd.to_numeric(scores, errors='coerce')
    
    # Replace NaN with 50 (neutral)
    import numpy as np
    scores = np.nan_to_num(scores, nan=50.0)

    # Normalize to roughly -1.0 to 1.0 (mean centered at 50, scaled by 50)
    normalized = (scores - 50.0) / 50.0
    
    return torch.tensor(normalized, dtype=torch.float32)

def get_synthetic_prior(pdi=0.50, idv=0.50, mas=0.50, uai=0.50):
    """
    Creates a direct synthetic Hofstede tensor. Used for assembling 'pure' theoretical personalities 
    like The Dogmatist or The Chaotic Agent, scaling inputs (0.0 - 1.0) into the Level 2 standard normal range.
    """
    import numpy as np
    scores = np.array([pdi * 100, idv * 100, mas * 100, uai * 100])
    
    # Normalize to roughly -1.0 to 1.0 (mean centered at 50, scaled by 50)
    normalized = (scores - 50.0) / 50.0
    return torch.tensor(normalized, dtype=torch.float32)
