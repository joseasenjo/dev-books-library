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

# Initialize session state for favorites
if "favorites" not in st.session_state:
    st.session_state.favorites = set()

# Load data
df = load_books()

# If data failed to load, show a friendly message and stop
if df.empty:
    st.error("❌ No se pudo cargar la biblioteca de libros. Intenta recargar la página más tarde.")
    st.stop()

# Sidebar – Filters
st.sidebar.title("🔎 Filters")

# Search input
search_term = st.sidebar.text_input("Search by title or author", placeholder="e.g., Python, Django")

# Language filter
languages = get_languages(df)
selected_languages = st.sidebar.multiselect("Language", languages, default=[])

# Format filter
formats = get_formats(df)
selected_formats = st.sidebar.multiselect("Format", formats, default=[])

# Category filter (if exists)
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

# Main area
st.title("📚 Dev Books Library")
st.caption("A curated collection of free programming books – powered by the EbookFoundation dataset")

# Stats row
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total books", len(df))
col2.metric("Filtered results", len(filtered_df))
col3.metric("Languages", len(languages))
col4.metric("Formats", len(formats))

# --- Visualizations (only if filtered data is not empty) ---
if not filtered_df.empty:
    # Distribution by language (top 15)
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
    
    # Optional: Format distribution
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

# --- Display books in a table ---
st.subheader("📖 Book List")

# Determine which columns to display
display_cols = ['title', 'author', 'language', 'format', 'url']
if 'category' in filtered_df.columns:
    display_cols.insert(2, 'category')

# Prepare display DataFrame
display_df = filtered_df[display_cols].copy()

if display_df.empty:
    st.info("No books to display.")
else:
    # Show the table with clickable links
    st.dataframe(
        display_df,
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

    # Download button
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download results (CSV)",
        data=csv,
        file_name="filtered_books.csv",
        mime="text/csv"
    )

# --- Favorites Section ---
st.sidebar.markdown("---")
st.sidebar.subheader("⭐ Favorites")

# Allow users to add favorites directly from the main table using a simple checkbox approach
st.subheader("⭐ Mark your favorite books")

# We'll use a data editor with a checkbox column to toggle favorites
# Create a copy of filtered_df with a 'Favorite' column
fav_df = filtered_df[['title', 'author', 'language']].copy()
fav_df['Favorite'] = fav_df['title'].apply(lambda x: x in st.session_state.favorites)

# Use st.data_editor to allow toggling favorites
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

# Button to save favorites from the editor
if st.button("💾 Save favorites"):
    # Update session state from the edited dataframe
    new_favs = set(edited_fav[edited_fav['Favorite']]['title'])
    st.session_state.favorites = new_favs
    st.success(f"Favorites updated ({len(new_favs)} books)")
    st.rerun()

# Display current favorites in sidebar
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
