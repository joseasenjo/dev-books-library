"""
Dev Books Library – Streamlit App
Search, filter, and explore thousands of free programming books.
"""

import streamlit as st
import pandas as pd
import altair as alt
from utils import (
    load_books,
    get_languages,
    get_formats,
    get_categories,
    filter_books,
    get_language_counts,
    get_format_counts,
    get_top_authors
)

# Page configuration
st.set_page_config(
    page_title="Dev Books Library",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "favorites" not in st.session_state:
    st.session_state.favorites = set()
if "retry_count" not in st.session_state:
    st.session_state.retry_count = 0

# --- Data Loading with Retry ---

def load_data():
    """Wrapper to load data with progress feedback."""
    with st.spinner("Loading library data... Please wait..."):
        df = load_books()
    return df

# Try to load data
df = load_data()

# If data is empty, show error and retry button
if df.empty:
    st.error("❌ Failed to load the book library. This could be due to network issues or the data source being temporarily unavailable.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Retry Loading", use_container_width=True):
            st.cache_data.clear()  # Clear cache to force fresh download
            st.session_state.retry_count += 1
            st.rerun()
    
    st.info("💡 You can also try refreshing the page or check your internet connection.")
    st.stop()  # Stop execution if no data

# --- Sidebar Filters ---
st.sidebar.title("🔎 Filters")

search_term = st.sidebar.text_input("Search by title or author", placeholder="e.g., Python, Django")

languages = get_languages(df)
selected_languages = st.sidebar.multiselect("Language", languages, default=[])

formats = get_formats(df)
selected_formats = st.sidebar.multiselect("Format", formats, default=[])

categories = get_categories(df)
selected_categories = st.sidebar.multiselect("Category", categories, default=[]) if categories else []

# Apply filters
filtered_df = filter_books(
    df,
    search_term=search_term,
    languages=selected_languages,
    formats=selected_formats,
    categories=selected_categories
)

# --- Main Content ---
st.title("📚 Dev Books Library")
st.caption("A curated collection of free programming books – powered by the EbookFoundation dataset")

# Stats
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total books", len(df))
col2.metric("Filtered results", len(filtered_df))
col3.metric("Languages", len(languages))
col4.metric("Formats", len(formats))

# Visualizations
if not filtered_df.empty:
    # Language distribution
    lang_counts = get_language_counts(filtered_df)
    if not lang_counts.empty:
        chart = alt.Chart(lang_counts.head(15)).mark_bar().encode(
            x=alt.X('language', sort='-y', title='Language'),
            y=alt.Y('count', title='Number of books'),
            tooltip=['language', 'count']
        ).properties(
            title='Books by Language (Top 15)',
            height=300
        )
        st.altair_chart(chart, use_container_width=True)
    
    # Format distribution (donut chart)
    format_counts = get_format_counts(filtered_df)
    if not format_counts.empty:
        format_chart = alt.Chart(format_counts).mark_arc(innerRadius=50).encode(
            theta="count",
            color="format",
            tooltip=["format", "count"]
        ).properties(
            title="Format Distribution",
            height=300
        )
        st.altair_chart(format_chart, use_container_width=True)
else:
    st.info("ℹ️ No books match your current filters. Try adjusting your search or filters.")

# --- Book Table ---
st.subheader("📖 Book List")

display_cols = ['title', 'author', 'language', 'format', 'url']
if 'category' in filtered_df.columns:
    display_cols.insert(2, 'category')

display_df = filtered_df[display_cols].copy()

if display_df.empty:
    st.info("No books to display.")
else:
    # Pagination keeps each render light even when thousands of rows match
    PAGE_SIZE = 50
    total_rows = len(display_df)
    total_pages = max(1, (total_rows - 1) // PAGE_SIZE + 1)

    page_col, info_col = st.columns([1, 3])
    with page_col:
        page = st.number_input(
            "Page", min_value=1, max_value=total_pages, value=1, step=1
        )
    with info_col:
        start = (page - 1) * PAGE_SIZE
        end = min(start + PAGE_SIZE, total_rows)
        st.caption(f"Showing {start + 1}-{end} of {total_rows} results · Page {page} of {total_pages}")

    st.dataframe(
        display_df.iloc[start:end],
        column_config={
            "url": st.column_config.LinkColumn("🔗 Link"),
            "title": "Title",
            "author": "Author",
            "language": "Language",
            "format": "Format",
            "category": "Category"
        },
        hide_index=True,
        use_container_width=True
    )

    # Download CSV (full filtered result, not just the current page)
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download all filtered results (CSV)",
        data=csv,
        file_name="filtered_books.csv",
        mime="text/csv"
    )

# --- Favorites ---
st.sidebar.markdown("---")
st.sidebar.subheader("⭐ Favorites")

st.subheader("⭐ Mark your favorite books")

fav_df = filtered_df[['title', 'author', 'language']].copy()
fav_df['Favorite'] = fav_df['title'].apply(lambda x: x in st.session_state.favorites)

edited_fav = st.data_editor(
    fav_df,
    column_config={
        "Favorite": st.column_config.CheckboxColumn("⭐ Favorite", default=False),
        "title": "Title",
        "author": "Author",
        "language": "Language"
    },
    hide_index=True,
    use_container_width=True,
    key="favorites_editor"
)

if st.button("💾 Save favorites"):
    new_favs = set(edited_fav[edited_fav['Favorite']]['title'])
    st.session_state.favorites = new_favs
    st.success(f"Favorites updated ({len(new_favs)} books)")
    st.rerun()

# Display favorites in sidebar
if st.session_state.favorites:
    fav_books = df[df['title'].isin(st.session_state.favorites)]
    if not fav_books.empty:
        st.sidebar.dataframe(fav_books[['title', 'author']], hide_index=True)
    else:
        st.sidebar.write("No favorites yet.")
else:
    st.sidebar.write("Click the star on any book to add it.")

# Footer
st.sidebar.markdown("---")
st.sidebar.info(
    "Data provided by [EbookFoundation](https://github.com/EbookFoundation/free-programming-books). "
    "Built with ❤️ using Streamlit."
)

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Built by <b>Jose Luis Asenjo</b> · "
    "<a href='https://www.linkedin.com/in/joseluisasenjo' target='_blank'>LinkedIn</a> &nbsp;|&nbsp; "
    "<a href='https://joseasenjo.github.io/portfolio/' target='_blank'>Portfolio</a>"
    "</div>",
    unsafe_allow_html=True
)
