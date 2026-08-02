"""
Utility functions for Dev Books Library.
Handles data loading, filtering, and statistics.
"""

import requests
import pandas as pd
import streamlit as st
from typing import List, Optional, Set
from rapidfuzz import fuzz, process

# --- Data Loading ---

@st.cache_data(ttl=86400, show_spinner=False)
def load_books() -> pd.DataFrame:
    """
    Load the book dataset from the official repository.
    Uses the jsdelivr CDN for maximum reliability and speed.
    Returns a pandas DataFrame with all books, or an empty DataFrame on failure.
    """
    # URL que ha funcionado de forma fiable
    url = "https://cdn.jsdelivr.net/gh/EbookFoundation/free-programming-books-search@main/fpb.json"
    
    try:
        with st.spinner("Loading library data..."):
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()
        
        if not data:
            st.warning("The dataset is empty.")
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Normalizar nombres de columnas: minúsculas y sin espacios
        df.columns = [col.lower().strip() for col in df.columns]
        
        # Asegurar que las columnas esenciales existen
        essential = ['title', 'author', 'language', 'format', 'url']
        for col in essential:
            if col not in df.columns:
                df[col] = None  # Añadir columna vacía si no existe
        
        # Eliminar filas sin título (no son útiles)
        df = df[df['title'].notna() & (df['title'] != '')]
        
        return df
    
    except requests.exceptions.Timeout:
        st.error("⏰ The request timed out. Please try again later.")
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
            filtered['_search_text'] = (filtered['title'].fillna('') + ' ' + filtered['author'].fillna('')).str.lower()
            
            if len(filtered) < 50000:
                texts = filtered['_search_text'].tolist()
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
                # Fallback para conjuntos de datos grandes
                filtered = filtered[
                    filtered['title'].str.contains(search_term, case=False, na=False) |
                    filtered['author'].str.contains(search_term, case=False, na=False)
                ]
            
            if '_search_text' in filtered.columns:
                filtered = filtered.drop(columns=['_search_text'])
        else:
            # Búsqueda simple por subcadena (insensible a mayúsculas)
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
