# from itertools import count
import re
import numpy as np
import pandas as pd
import operator as op
from uuid import uuid4
import pycountry
from pyserini.search import LuceneSearcher, FaissSearcher
from pyserini.search.hybrid import HybridSearcher

from encoder import SentenceTransformerEncoder


def load_data(path, langs):
    df = pd.read_csv(path, sep='\t')
    if 'uuid' not in df.columns:
        df['uuid'] = [uuid4() for _ in range(df.shape[0])]
        df.to_csv(path, index=False, sep='\t')
    df = df[df['lang'].isin(langs)]  # filter relevant language
    return df


def get_country(code: str) -> str:
    if code:
        country = pycountry.countries.get(alpha_2=code)
        if country:
            # print(country.name)
            return country.name
        else:
            if "-" in code:
                cs = code.split("-")
                country = pycountry.countries.get(alpha_2=cs[0])
                if country:
                    return country.name+f" ({'-'.join(cs[1:])})"
            return code
    else:
        return ""


def load_corpus(corpus_path, langs, pattern):
    corpus_df = load_data(corpus_path, langs)
    corpus_df["sentence"] = corpus_df["sentence"].apply(lambda x: np.nan if x == "" else x)
    corpus_df["uuid"] = corpus_df["uuid"].apply(lambda x: str(x))
    corpus_df = corpus_df.dropna(subset=["sentence"])
    corpus_df = corpus_df.drop_duplicates(subset="id")
    corpus_df = corpus_df.drop_duplicates()
    corpus_df.index = corpus_df["uuid"].apply(lambda x: str(x))
    corpus_df["sentence"] = corpus_df["sentence"].apply(lambda x: x.lower())
    corpus_df["alpha_sentence"] = corpus_df["sentence"].apply(lambda x: re.sub(pattern, '', x).lower())
    corpus_df["countries"] = corpus_df["countries"].apply(lambda x: x.replace("'","").replace(" ", "").replace("[", "").replace("]", "").split(","))
    corpus_df["countries"] = corpus_df["countries"].apply(lambda x: [get_country(c) for c in x])
    return corpus_df


def filter_years(corpus_df, year):
    corpus_df = corpus_df[(corpus_df["date"] >= year[0]) & (corpus_df["date"] <= year[1])]
    return corpus_df


def filter_corpus(corpus_df, values, column, row_type=list):
    def check_op(all_rows, list2, rtype):
        rows = []
        for i,row in enumerate(all_rows):
            if rtype == list:
                for e in list2:
                    if op.countOf(row, e) > 0:
                        rows.append(i)
            elif rtype == str:
                for e in list2:
                    if e in row:
                        rows.append(i)
        return rows

    idxs = check_op(corpus_df[column].tolist(), values, row_type)
    corpus_df = corpus_df.loc[corpus_df.index[idxs]]
    return corpus_df


def load_searchers(index_name, model_name):
    ssearcher = LuceneSearcher(index_name)
    
    encoder = SentenceTransformerEncoder(model_name)
    dsearcher = FaissSearcher(index_name, encoder)

    hsearcher = HybridSearcher(sparse_searcher=ssearcher, dense_searcher=dsearcher)
    return hsearcher
