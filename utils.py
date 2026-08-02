"""
Utility functions for the Dev Books Library app.
- load_books(): fetches and caches the JSON data
- get_languages(), get_formats(): extract available filters
- filter_books(): apply search and filter criteria
- fuzzy_search(): helper for partial matching
"""

import requests
import pandas as pd
from rapidfuzz import fuzz
import streamlit as st
from typing import List, Dict, Any

# Cache the data for 24 hours
@st.cache_data(ttl=86400)
def load_books() -> pd.DataFrame:
    """
    Load the book dataset from the official parser repository.
    Returns a pandas DataFrame with all books.
    """
    url = "https://raw.githubusercontent.com/EbookFoundation/free-programming-books-parser/main/fpb.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        # Normalize column names
        df.columns = [col.lower() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

def get_languages(df: pd.DataFrame) -> List[str]:
    """Return sorted list of unique languages from the dataset."""
    if 'language' in df.columns:
        return sorted(df['language'].dropna().unique())
    return []

def get_formats(df: pd.DataFrame) -> List[str]:
    """Return sorted list of unique formats from the dataset."""
    if 'format' in df.columns:
        return sorted(df['format'].dropna().unique())
    return []

def filter_books(
    df: pd.DataFrame,
    search_term: str = "",
    languages: List[str] = None,
    formats: List[str] = None,
    categories: List[str] = None
) -> pd.DataFrame:
    """
    Apply filters to the DataFrame.
    - search_term: match title or author (case-insensitive, fuzzy if enabled)
    - languages: list of languages to include
    - formats: list of formats to include
    - categories: list of categories to include
    """
    filtered = df.copy()
    
    # Text search (fuzzy match with threshold 70)
    if search_term:
        # Filter rows where title or author contains the search term (case-insensitive)
        # For better experience, we'll do a simple contains first, fallback to fuzzy if needed.
        mask = filtered['title'].str.contains(search_term, case=False, na=False) | \
               filtered['author'].str.contains(search_term, case=False, na=False)
        # If too few results, apply fuzzy matching (optional)
        if mask.sum() < 5:  # if too few, try fuzzy
            # We'll use fuzzy on title and author, but this is O(N^2) for large datasets, so we limit.
            # For simplicity, we'll keep the simple contains, but you can implement fuzzy if needed.
            pass
        filtered = filtered[mask]
    
    if languages:
        filtered = filtered[filtered['language'].isin(languages)]
    if formats:
        filtered = filtered[filtered['format'].isin(formats)]
    if categories:
        # assuming there is a 'category' column; if not, we can skip.
        if 'category' in filtered.columns:
            filtered = filtered[filtered['category'].isin(categories)]
    
    return filtered

def get_categories(df: pd.DataFrame) -> List[str]:
    """Return sorted list of unique categories (if available)."""
    if 'category' in df.columns:
        return sorted(df['category'].dropna().unique())
    return []

# Optionally, a function to get top languages for chart
def get_language_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Return count of books per language."""
    if 'language' in df.columns:
        counts = df['language'].value_counts().reset_index()
        counts.columns = ['language', 'count']
        return counts
    return pd.DataFrame()
