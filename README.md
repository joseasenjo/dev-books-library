# 📚 Dev Books Library

Aplicación en Streamlit para buscar, filtrar y explorar miles de libros, cursos y screencasts **gratuitos** sobre programación y desarrollo de software, en decenas de idiomas.

🔗 **Demo en vivo:** https://dev-books-library.streamlit.app/

Los datos provienen del catálogo de [EbookFoundation/free-programming-books](https://github.com/EbookFoundation/free-programming-books), uno de los repositorios de recursos gratuitos de programación más completos de GitHub.

## Características

- 🔎 **Búsqueda** por título o autor.
- 🌍 **Filtros** por idioma, formato (PDF, HTML, EPUB...) y categoría (📚 Libros, 🎓 Cursos, 🎧 Screencasts, 🔧 Otros).
- 📊 **Visualizaciones**: distribución de recursos por idioma y por formato.
- ⭐ **Favoritos**: marca los recursos que te interesan durante la sesión.
- 📄 **Paginación** de resultados para no sobrecargar la tabla con miles de filas.
- 📥 **Exportación a CSV** del conjunto de resultados filtrado.

## Stack técnico

- [Streamlit](https://streamlit.io/) — interfaz y despliegue
- [pandas](https://pandas.pydata.org/) — procesado de datos
- [Altair](https://altair-viz.github.io/) — gráficos
- [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) — búsqueda difusa (fuzzy search)
- [Requests](https://requests.readthedocs.io/) — descarga del dataset

## Origen y procesado de los datos

El dataset se descarga en formato JSON (`fpb.json`) desde el repositorio de EbookFoundation, con varias URLs de respaldo por si alguna falla. Internamente, ese JSON tiene forma de **árbol anidado**:

```
root → categoría (books / casts / courses / more) → idioma → secciones → entradas
```

`utils.py` incluye un parser recursivo (`_parse_fpb_tree`) que recorre ese árbol y lo aplana en un DataFrame con columnas homogéneas (`title`, `author`, `language`, `format`, `url`, `category`), sobre el que luego se aplican los filtros de la interfaz.

## Instalación y ejecución local

```bash
git clone https://github.com/joseasenjo/dev-books-library.git
cd dev-books-library
pip install -r requirements.txt
streamlit run app.py
```

La app se abrirá en `http://localhost:8501`.

## Estructura del proyecto

```
.
├── app.py              # Interfaz Streamlit (filtros, tabla, gráficos, favoritos)
├── utils.py             # Carga y parseo de datos, filtrado, estadísticas
├── requirements.txt      # Dependencias
└── .streamlit/
    └── config.toml       # Tema y configuración de Streamlit
```

## Autor

**Jose Luis Asenjo**
🔗 [LinkedIn](https://www.linkedin.com/in/joseluisasenjo) · 💼 [Portfolio](https://joseasenjo.github.io/portfolio/)

## Licencia y créditos

Este proyecto solo indexa y presenta metadatos (título, autor, enlace) del catálogo público de [EbookFoundation/free-programming-books](https://github.com/EbookFoundation/free-programming-books). Todo el contenido enlazado pertenece a sus respectivos autores y editores.
