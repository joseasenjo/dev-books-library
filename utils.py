"""
Utility functions for Dev Books Library.
Handles data loading with multiple fallbacks and robust error handling.
"""

import requests
import pandas as pd
import streamlit as st
import time
from typing import List, Optional, Set
from rapidfuzz import fuzz, process

# --- Data Loading with Multiple Fallbacks ---

CATEGORY_LABELS = {
    'books': '📚 Books',
    'casts': '🎧 Screencasts',
    'courses': '🎓 Courses',
    'more': '🔧 Other',
}


def _extract_entries(section: dict, language: str, category: str, rows: list) -> None:
    """Recursively walk a section's entries/subsections and append flat book rows."""
    for entry in section.get('entries') or []:
        title = entry.get('title')
        if not title:
            continue
        notes = entry.get('notes') or []
        rows.append({
            'title': title,
            'author': entry.get('author') or 'Unknown',
            'language': language,
            'format': ', '.join(notes) if notes else 'N/A',
            'url': entry.get('url'),
            'category': category,
        })
    for sub in section.get('subsections') or []:
        _extract_entries(sub, language, category, rows)


def _parse_fpb_tree(data: dict) -> pd.DataFrame:
    """
    Flatten the nested free-programming-books-search JSON tree
    (root -> category[books/casts/courses/more] -> language -> sections -> entries)
    into a flat DataFrame of individual resources.
    """
    rows: list = []
    for top in data.get('children') or []:
        raw_category = top.get('type', 'other')
        category = CATEGORY_LABELS.get(raw_category, raw_category)
        for lang_node in top.get('children') or []:
            language = (lang_node.get('language') or {}).get('name') or 'Unknown'
            for section in lang_node.get('sections') or []:
                _extract_entries(section, language, category, rows)
    return pd.DataFrame(rows)


@st.cache_data(ttl=86400, show_spinner=False)
def load_books(force_reload: bool = False) -> pd.DataFrame:
    """
    Load the book dataset from multiple sources with retries.
    - force_reload: if True, bypass cache and force a fresh download.
    Returns a pandas DataFrame with all books, or an empty DataFrame on failure.
    """
    # Lista de URLs probadas (ordenadas por fiabilidad)
    urls = [
        "https://cdn.jsdelivr.net/gh/EbookFoundation/free-programming-books-search@main/fpb.json",
        "https://raw.githubusercontent.com/EbookFoundation/free-programming-books-search/main/fpb.json",
        "https://ebookfoundation.github.io/free-programming-books-search/fpb.json",
    ]

    last_error = None

    for url in urls:
        for attempt in range(1, 4):  # 3 intentos por URL
            try:
                with st.spinner(f"Loading data from source {urls.index(url)+1} (attempt {attempt})..."):
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    data = response.json()

                if not data:
                    continue  # Si viene vacío, probar siguiente URL

                # El JSON es un árbol anidado (root -> categoría -> idioma -> secciones -> entries),
                # no una lista plana de libros: hay que aplanarlo antes de usarlo.
                if isinstance(data, dict) and 'children' in data:
                    df = _parse_fpb_tree(data)
                else:
                    df = pd.DataFrame(data)

                # Normalizar columnas
                df.columns = [col.lower().strip() for col in df.columns]

                # Asegurar columnas esenciales
                essential = ['title', 'author', 'language', 'format', 'url']
                for col in essential:
                    if col not in df.columns:
                        df[col] = None

                # Eliminar filas sin título
                df = df[df['title'].notna() & (df['title'] != '')]

                # Si tenemos al menos un libro, retornar éxito
                if len(df) > 0:
                    return df

            except requests.exceptions.Timeout:
                last_error = "Timeout"
                continue
            except requests.exceptions.HTTPError as e:
                last_error = f"HTTP {e.response.status_code}"
                if e.response.status_code == 404:
                    break  # Si es 404, esta URL no existe, pasar a la siguiente
                continue
            except requests.exceptions.ConnectionError:
                last_error = "Connection error"
                continue
            except requests.exceptions.JSONDecodeError:
                last_error = "Invalid JSON"
                continue
            except Exception as e:
                last_error = str(e)
                continue
        
        # Si después de 3 intentos falla, pasar a la siguiente URL
        continue
    
    # Si todas las URLs fallaron, mostrar error detallado
    st.error(f"❌ Failed to load data from all sources. Last error: {last_error}")
    st.info("💡 You can try reloading the page or click the 'Retry' button below.")
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
                filtered = filtered[
                    filtered['title'].str.contains(search_term, case=False, na=False) |
                    filtered['author'].str.contains(search_term, case=False, na=False)
                ]
            
            if '_search_text' in filtered.columns:
                filtered = filtered.drop(columns=['_search_text'])
        else:
            filtered = filtered[
                filtered['title'].str.contains(search_term, case=False, na=False) |
                filtered['author'].str.contains(search_term, case=False, na=False)
            ]
    
    return filtered


# --- Statistics ---

def get_language_counts(df: pd.DataFrame) -> pd.DataFrame:
    if 'language' in df.columns:
        counts = df['language'].value_counts().reset_index()
        counts.columns = ['language', 'count']
        return counts
    return pd.DataFrame(columns=['language', 'count'])


def get_format_counts(df: pd.DataFrame) -> pd.DataFrame:
    if 'format' in df.columns:
        counts = df['format'].value_counts().reset_index()
        counts.columns = ['format', 'count']
        return counts
    return pd.DataFrame(columns=['format', 'count'])


def get_top_authors(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if 'author' in df.columns:
        counts = df['author'].value_counts().head(top_n).reset_index()
        counts.columns = ['author', 'count']
        return counts
    return pd.DataFrame(columns=['author', 'count'])


# --- Favorites utility ---

def toggle_favorite(book_title: str, favorites: Set[str]) -> Set[str]:
    if book_title in favorites:
        favorites.remove(book_title)
    else:
        favorites.add(book_title)
    return favorites
