import re
# import string
import streamlit as st
import logging

from config import Settings
from helper import load_corpus, load_searchers, filter_corpus, filter_years

st.set_page_config(page_title="Variable Search", page_icon="🔎")

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


sidebar_description = """
    **This website saves the text that you write in the search input field. This data is used to improve the search engine.**
    
    __Info__:

    This site allows you to search for survey items (i.e., variables) from surveys such as Eurobarometer, ISSP, EVS, and more.
    Using language models, the input is semantically compared against the question text of survey items.
    Ideally, the results should contain the same or similar semantic information as your input.
    You can filter the search results by year or country of the survey. 

    __How to use__:

    1. Select a pre-defined input or enter a search query in the search input field.
    2. Select one or more countries from the list under "Geography" or leave it empty.
    3. Select a study group or leave it empty.
    4. Select the range of years to be included in the search results.
    5. Click on the search button.
    6. Evaluate the results by clicking on "Show X more survey item(s)" to expand the list of results that contain an identical question.

    __NOTE__:

    __Longitudal Studies__: Variables that are grouped together often originate from longitudal studies (i.e., repeated measures over long periods of time).

    __Concept Search__: While the search system will perform best for finding texts that are semantically-similar to the input, you may also try more abstract inputs such as concepts (e.g., "financial literacy"). While the system is not specifically designed to retrieve variables that are related to concepts, language models (having seen a large part of the internet) may map concepts to texts similar to the variables that are used to operationalize and measure them.
"""
st.sidebar.markdown(sidebar_description)


st.title("Variable Search")
st.markdown(f"Search across survey items (i.e., variables) from surveys such as Eurobarometer, ISSP, EVS, and more.<br>In total, you can search for over 80,000 items.", unsafe_allow_html=True)


@st.cache_data
def prepare_data(corpus_path, langs, pattern):
    return load_corpus(corpus_path, langs, pattern)


@st.cache_resource
def prepare_models(index_name, model_name_or_path):
    return load_searchers(index_name, model_name_or_path)


def prepare(settings, langs, pattern):
    langs = sorted(settings.languages.split(','))
    # logging.info("Preparing data...")
    df = prepare_data(settings.corpus_path, langs, pattern)
    # logging.info("Done.")
    # logging.info("Preparing models...")
    hsearcher = prepare_models(settings.index_name, settings.model_name_or_path)
    # logging.info("Done.")
    return df, hsearcher

try:
    st.info("Please note, the **text** that you write into the text box **is saved** to improve the search engine.")
    
    settings = Settings()
    
    query = st.selectbox("Pre-defined inputs:", ["Another query (via 'Search input')..."]+settings.predefined_inputs, key="pre-query")
    # query = st.selectbox("Pre-defined inputs:", ["Another query (via 'Search input')...", "Do you have a job?", "Are you happy with the healthcare system?"])
    
    col1, col2 = st.columns([9,1])
    
    if query == "Another query (via 'Search input')...":
        with col1:
        # query = st.selectbox("Pre-defined Queries:", ["Other query", "Do you have a job?", "Are you happy with the healthcare system?"])
            query = st.text_input(label="Search input:", placeholder="Do you have a job?", key="query")
    
        with col2:
            st.write('#')
            button_clicked = st.button("🔎")
    else:
        button_clicked = False
    
    langs = sorted(settings.languages.split(','))
    pattern = re.compile(r'[\W_]+')
    
    corpus_df, hsearcher = prepare(settings, langs, pattern)
    
    all_countries = sorted(list(set([c for cs in corpus_df["countries"].tolist() for c in cs if c and "_" not in c])))
    countries = st.multiselect("Geography:", all_countries, key="countries")
    if countries:
        corpus_df = filter_corpus(corpus_df, countries, column="countries")
    
    all_study_groups = sorted(list(set(corpus_df["title"].tolist())))
    study_groups = st.multiselect("Study Group:", all_study_groups, key="study_groups")
    if study_groups:
        corpus_df = filter_corpus(corpus_df, study_groups, column="title", row_type=str)
    
    unique_years = list(set([int(x) for x in corpus_df["date"].tolist() if isinstance(x, str) or isinstance(x, int)]))
    if unique_years:
        min_year, max_year = min(unique_years), max(unique_years)
        if min_year < max_year:
            year = st.slider("Publication Year:", min_year, max_year, (min_year, max_year), 1, key="year")
            corpus_df = filter_years(corpus_df, year)
        else:
            year = min_year
            st.markdown(f"Year: {min_year}")
            st.markdown("---")
    else:
        year = None
    
    corpus_groups = corpus_df.groupby(by='alpha_sentence')
    
    try:
        if (query or button_clicked) and query != "":
            logging.info(f"Query: '{query}'")
            logging.info(f"Geography: {countries}")
            logging.info(f"Min/max Years: {year}")
    
            with st.spinner("Searching..."):
                hits = hsearcher.search(query, alpha=settings.alpha, k0=settings.top_k, k=settings.top_k, normalization=settings.normalization, weight_on_dense=settings.weight_on_dense)
                result_sentences = []
                for hit in hits:
                    _id = hit.docid
                    if _id in corpus_df.index:
                        result_sentence = corpus_df.loc[_id]["sentence"]
                        result_sentence = re.sub(pattern, '', result_sentence).lower()
                        if result_sentence not in result_sentences:
                            result_sentences.append(result_sentence)
    
                st.write(f"<i>Showing the top {len(result_sentences)} result(s) out of {len(corpus_groups.groups)} question(s).</i>", unsafe_allow_html=True)
                st.write("---")
    
                # ogroups = sorted(corpus_groups.groups.items(), key=lambda x: x[1][0])
                for j,sentence in enumerate(result_sentences):
                    if sentence in corpus_groups.groups:
                        group = corpus_groups.get_group(sentence)
                        osentence = group.iloc[0].get('sentence', '')
    
                        st.markdown(f'Question: {osentence}', unsafe_allow_html=True)
                        expander_text = f'Show {group.shape[0]} grouped survey items.' if group.shape[0] > 1 else f'Show {group.shape[0]} grouped survey item.'
                        modal = st.expander(expander_text)
                        for i in range(group.shape[0]):
                            row = group.iloc[i]
                            rid = row.get('id', '')
                            rlabel = row.get('label', '')
                            rsq = row.get('sub-question', '')
                            ritem = row.get('item_category', '')
                            rtitle = row.get('title', '')
                            if rtitle and rid:
                                rtitle = f'<a href="https://search.gesis.org/research_data/{rid.split("_")[0]}">{rtitle}</a>'
                            rdate = row.get('date', '')  # TODO: what is this date?
                            rcountries = row.get('countries', '')
                            rqt1 = row.get('question_type1', '')
                            rqt2 = row.get('question_type2', '')
    
                            modal.markdown(f'<a href="https://search.gesis.org/variables/exploredata-{rid}">{rid}</a>\
                                            <br>Label: {rlabel}\
                                            <br>Sub-Question: {rsq}\
                                            <br>Item: {ritem}\
                                            <br>Research Data: {rtitle}\
                                            <br>Study Date: {rdate}\
                                            <br>Geography: {rcountries}\
                                            <br>Question Type 1: {rqt1}\
                                            <br>Question Type 2: {rqt2}',
                                            unsafe_allow_html=True
                                        )
                            if i+1 < group.shape[0] > 1:
                                modal.markdown('---')
    
                        if j+1 < len(result_sentences) > 1:
                            st.markdown('---')
                    else:
                        logging.debug(f"Sentence is not in groups: {sentence}")
    except:
        st.error("Something went wrong. Please try again with a different input.")
        logging.warning(f'An error occurred for the query: {query}')
except:
    st.error("Something went wrong. Please try again later.")
    logging.warning(f'The app crashed.')
