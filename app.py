"""
Dev Books Library – Streamlit App
Search, filter, and explore thousands of free programming books.
"""

import streamlit as st
import pandas as pd
import altair as alt
from utils import load_books, get_languages, get_formats, get_categories, filter_books, get_language_counts

# Page configuration
st.set_page_config(
    page_title="Dev Books Library",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load data
df = load_books()
if df.empty:
    st.stop()

# Session state for favorites
if "favorites" not in st.session_state:
    st.session_state.favorites = set()

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
st.caption("A curated collection of over 7,000 free programming books")

# Stats row
col1, col2, col3 = st.columns(3)
col1.metric("Total books", len(df))
col2.metric("Filtered results", len(filtered_df))
col3.metric("Languages available", len(languages))

# Chart: distribution by language (of filtered results)
if not filtered_df.empty:
    lang_counts = get_language_counts(filtered_df)
    if not lang_counts.empty:
        chart = alt.Chart(lang_counts.head(15)).mark_bar().encode(
            x=alt.X('language', sort='-y', title='Language'),
            y=alt.Y('count', title='Number of books'),
            tooltip=['language', 'count']
        ).properties(
            title='Books by Language (top 15)',
            height=300
        )
        st.altair_chart(chart, use_container_width=True)

# Display books
st.subheader("📖 Book List")
if filtered_df.empty:
    st.info("No books match your criteria. Try adjusting filters.")
else:
    # Prepare display columns
    display_cols = ['title', 'author', 'language', 'format', 'url']
    # If category exists, add it
    if 'category' in filtered_df.columns:
        display_cols.insert(2, 'category')
    
    # Create a copy for display
    display_df = filtered_df[display_cols].copy()
    
    # Add a "Favorite" column with buttons (using session state)
    # We'll use a checkbox or button per row, but for simplicity we'll show favorites in another section.
    # Let's add a "Add to favorites" button column using st.dataframe with column config (not straightforward)
    # Alternative: use st.data_editor with a custom column for favorites.
    # We'll implement a simple favorite toggle using a separate section and buttons.
    
    # For now, we'll just show the table with links
    st.dataframe(
        display_df,
        column_config={
            "url": st.column_config.LinkColumn("🔗 Link"),
            "title": "Title",
            "author": "Author",
            "language": "Language",
            "format": "Format",
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Download filtered results as CSV
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download results (CSV)",
        data=csv,
        file_name="filtered_books.csv",
        mime="text/csv"
    )

# Favorites section (optional)
st.sidebar.markdown("---")
st.sidebar.subheader("⭐ Favorites")
if st.session_state.favorites:
    fav_df = df[df['title'].isin(st.session_state.favorites)]
    if not fav_df.empty:
        st.sidebar.dataframe(fav_df[['title', 'author']], hide_index=True)
    else:
        st.sidebar.write("No favorites yet.")
else:
    st.sidebar.write("Click the star on any book to add it.")

# Add a simple way to add/remove favorites (e.g., from the table, but we'll need to handle on click)
# For a more advanced version, you could implement a button per row using st.columns inside a loop.
# For brevity, I'll demonstrate a basic version: in the main area, we can have a "Add to favorites" button for each book.
# But that's not efficient for large datasets. Instead, we'll use a simple selectbox or allow users to input a title.
# Alternatively, we can add a "Favorite" checkbox in the dataframe using st.data_editor with a column of booleans.
# Let's implement the data_editor approach:
st.subheader("⭐ Mark your favorites")
# Create a copy and add a checkbox column
edit_df = filtered_df[['title', 'author', 'language', 'format', 'url']].copy()
edit_df['Favorite'] = edit_df['title'].apply(lambda x: x in st.session_state.favorites)

# Use st.data_editor to allow toggling favorites
edited = st.data_editor(
    edit_df,
    column_config={
        "url": st.column_config.LinkColumn("Link"),
        "Favorite": st.column_config.CheckboxColumn("⭐ Favorite", default=False),
    },
    hide_index=True,
    use_container_width=True,
    key="favorite_editor"
)

# Update favorites based on changes
# We need to detect which rows have been toggled
# But st.data_editor returns the entire dataframe, so we can compare
if 'edited' in st.session_state and st.session_state.edited:
    # For simplicity, we'll just update the set from the edited dataframe
    new_favs = set(edited[edited['Favorite']]['title'])
    st.session_state.favorites = new_favs
    st.rerun()  # to reflect changes
else:
    # On first load, ensure the editor reflects the session state
    pass

# We need to store the edited state in session to avoid rerun loops
# Actually, we can just update when user interacts. Let's simplify: we'll use a button to save favorites.
# But the data_editor approach is interactive; we can update on change by using a callback.
# For simplicity, we'll just rely on the data_editor and when the user clicks a checkbox, it updates the session state.
# However, data_editor does not automatically update session_state. We need to capture the changes.
# One way: use a button to "Update favorites" that reads the edited dataframe.
# I'll implement a button:

if st.button("💾 Update favorites"):
    fav_titles = set(edited[edited['Favorite']]['title'])
    st.session_state.favorites = fav_titles
    st.success(f"Favorites updated ({len(fav_titles)} books)")
    st.rerun()

# Footer
st.sidebar.markdown("---")
st.sidebar.info(
    "Data provided by [EbookFoundation](https://github.com/EbookFoundation/free-programming-books). "
    "Built with ❤️ using Streamlit."
)
