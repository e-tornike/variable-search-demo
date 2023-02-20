class Settings:
    root_dir = './data/embeddings/'
    corpus_path = './data/full.tsv'
    model_name_or_path: str = 'intfloat/e5-small'
    index_name = 'test-index'
    # max_corpus_size = 500000
    # n_clusters = 64
    # nprobe = 3
    languages = 'en'
    top_k = 100
    alpha = 2.0
    normalization = True
    weight_on_dense = False