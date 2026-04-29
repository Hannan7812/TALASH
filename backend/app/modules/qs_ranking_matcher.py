import os
import re
import pandas as pd
from difflib import SequenceMatcher

QS_RANKING_PATH = os.path.join(
    os.path.dirname(__file__), 
    "..", "..", "qs_rankings", 
    "2026 QS World University Rankings 1.3 (For qs.com).xlsx"
)

_QS_DF = None

def get_qs_ranking(uni_name: str) -> tuple[str, int | None]:
    if not uni_name:
        return uni_name, None
        
    global _QS_DF
    if _QS_DF is None:
        if not os.path.exists(QS_RANKING_PATH):
            return uni_name, None
        # The actual headers are on row 2 (index 2 in pandas when skipping row 0, 1)
        _QS_DF = pd.read_excel(QS_RANKING_PATH, header=2)
        
    if _QS_DF.empty:
        return uni_name, None
        
    def clean_name(name):
        if not isinstance(name, str): 
            return ""
        name = name.lower()
        name = re.sub(r'[^a-z0-9\s]', ' ', name)
        words = [w for w in name.split() if w not in {'of', 'and', 'the', 'at', 'in', 'for'}]
        return " ".join(words)
        
    search_str = clean_name(uni_name)
    if not search_str:
        return uni_name, None
        
    if 'Name' not in _QS_DF.columns or 'Rank' not in _QS_DF.columns:
        return uni_name, None
        
    best_match = None
    best_ratio = 0.0
    best_rank = None
    
    for _, row in _QS_DF.iterrows():
        row_name = row['Name']
        if not isinstance(row_name, str): 
            continue
            
        c_row_name = clean_name(row_name)
        
        ratio = SequenceMatcher(None, search_str, c_row_name).ratio()
        
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = row_name
            best_rank = row['Rank']

        if search_str == c_row_name or (search_str in c_row_name and len(search_str) > 10) or (c_row_name in search_str and len(c_row_name) > 10):
            best_ratio = 1.0
            best_match = row_name
            best_rank = row['Rank']
            break
            
    if best_ratio > 0.85 and best_match:
        rank_val = best_rank
        if isinstance(rank_val, str):
            nums = re.findall(r'\d+', rank_val)
            if nums:
                return best_match, int(nums[0])
        elif isinstance(rank_val, (int, float)):
            return best_match, int(rank_val)
                
    return uni_name, None
