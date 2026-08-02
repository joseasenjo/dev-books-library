"""
Utility functions for Dev Books Library.
Handles data loading, filtering, and statistics.
"""

import requests
import pandas as pd
import streamlit as st
from typing import List, Optional, Set
from rapidfuzz import fuzz, process
from functools import lru_cache

# --- Data Loading ---

@st.cache_data(ttl=86400, show_spinner=False)
def load_books() -> pd.DataFrame:
    """
    Load the book dataset from the official parser repository.
    Uses the 'master' branch (the default branch of the parser repo).
    Returns a pandas DataFrame with all books, or an empty DataFrame on failure.
    """
    url = "https://raw.githubusercontent.com/EbookFoundation/free-programming-books-parser/master/fpb.json"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        
        if not data:
            st.warning("The dataset is empty.")
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Normalize column names: lowercase and strip spaces
        df.columns = [col.lower().strip() for col in df.columns]
        
        # Ensure essential columns exist
        essential = ['title', 'author', 'language', 'format', 'url']
        for col in essential:
            if col not in df.columns:
                df[col] = None  # Add missing columns as empty
        
        # Drop rows with no title (they are useless)
        df = df[df['title'].notna() & (df['title'] != '')]
        
        return df
    
    except requests.exceptions.Timeout:
        st.error("⏰ Request timed out. Please try again later.")
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ HTTP error: {e}")
    except requests.exceptions.ConnectionError:
        st.error("🌐 Connection error. Please check your internet connection.")
    except requests.exceptions.JSONDecodeError:
        st.error("📄 Invalid JSON response from the server.")
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
    
    return pd.DataFrame()


# --- Filtering and Extraction ---

def get_languages(df: pd.DataFrame) -> List[str]:
    """Return a sorted list of unique languages present in the dataset."""
    if 'language' in df.columns:
        langs = df['language'].dropna().unique()
        return sorted([str(lang) for lang in langs if lang])
    return []


def get_formats(df: pd.DataFrame) -> List[str]:
    """Return a sorted list of unique formats present in the dataset."""
    if 'format' in df.columns:
        fmts = df['format'].dropna().unique()
        return sorted([str(fmt) for fmt in fmts if fmt])
    return []


def get_categories(df: pd.DataFrame) -> List[str]:
    """Return a sorted list of unique categories (if the column exists)."""
    if 'category' in df.columns:
        cats = df['category'].dropna().unique()
        return sorted([str(cat) for cat in cats if cat])
    return []


def filter_books(
    df: pd.DataFrame,
    search_term: str = "",
    languages: Optional[List[str]] = None,
    formats: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    use_fuzzy: bool = False,
    fuzzy_threshold: int = 70
) -> pd.DataFrame:
    """
    Apply filters to the DataFrame.
    - search_term: case-insensitive search in title and author.
    - languages, formats, categories: lists of allowed values (exact matches).
    - use_fuzzy: if True, use fuzzy matching for search_term.
    - fuzzy_threshold: minimum score (0-100) for fuzzy match.
    Returns a filtered DataFrame.
    """
    filtered = df.copy()
    
    # --- Language filter ---
    if languages:
        filtered = filtered[filtered['language'].isin(languages)]
    
    # --- Format filter ---
    if formats:
        filtered = filtered[filtered['format'].isin(formats)]
    
    # --- Category filter ---
    if categories and 'category' in filtered.columns:
        filtered = filtered[filtered['category'].isin(categories)]
    
    # --- Text search ---
    if search_term:
        search_term = search_term.strip()
        if use_fuzzy:
            # Fuzzy search: compute similarity on title+author
            # We'll create a combined text column for matching
            filtered['_search_text'] = (filtered['title'].fillna('') + ' ' + filtered['author'].fillna('')).str.lower()
            # Use process.extract to get matches above threshold
            # This is O(N) per search, but we can cache results per term? Not needed.
            # For performance, we'll only fuzzy if dataset is not huge (< 100k)
            if len(filtered) < 50000:
                # Get list of texts and indices
                texts = filtered['_search_text'].tolist()
                # Use rapidfuzz's extract to get indices of matches above threshold
                matches = process.extract(
                    query=search_term.lower(),
                    choices=texts,
                    scorer=fuzz.partial_ratio,
                    limit=None,
                    score_cutoff=fuzzy_threshold
                )
                matched_indices = [i for i, (_, score, idx) in enumerate(matches)]
                filtered = filtered.iloc[matched_indices]
            else:
                # Fallback to simple contains for large datasets
                filtered = filtered[
                    filtered['title'].str.contains(search_term, case=False, na=False) |
                    filtered['author'].str.contains(search_term, case=False, na=False)
                ]
            # Drop temporary column
            if '_search_text' in filtered.columns:
                filtered = filtered.drop(columns=['_search_text'])
        else:
            # Simple substring search (case-insensitive)
            filtered = filtered[
                filtered['title'].str.contains(search_term, case=False, na=False) |
                filtered['author'].str.contains(search_term, case=False, na=False)
            ]
    
    return filtered


# --- Statistics ---

def get_language_counts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a DataFrame with counts of books per language.
    """
    if 'language' in df.columns:
        counts = df['language'].value_counts().reset_index()
        counts.columns = ['language', 'count']
        return counts
    return pd.DataFrame(columns=['language', 'count'])


def get_format_counts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a DataFrame with counts of books per format.
    """
    if 'format' in df.columns:
        counts = df['format'].value_counts().reset_index()
        counts.columns = ['format', 'count']
        return counts
    return pd.DataFrame(columns=['format', 'count'])


def get_top_authors(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Return the top N authors by number of books.
    """
    if 'author' in df.columns:
        counts = df['author'].value_counts().head(top_n).reset_index()
        counts.columns = ['author', 'count']
        return counts
    return pd.DataFrame(columns=['author', 'count'])


# --- Utility for session state favorites (optional) ---

def toggle_favorite(book_title: str, favorites: Set[str]) -> Set[str]:
    """
    Toggle a book title in the favorites set.
    Returns the updated set.
    """
    if book_title in favorites:
        favorites.remove(book_title)
    else:
        favorites.add(book_title)
    return favorites


# --- For testing / debugging (optional) ---

if __name__ == "__main__":
    # Quick test: load data and show basic info
    df = load_books()
    if not df.empty:
        print(f"Loaded {len(df)} books.")
        print("Columns:", df.columns.tolist())
        print("Languages:", get_languages(df)[:5])
        print("Formats:", get_formats(df)[:5])
    else:
        print("Failed to load data.")
