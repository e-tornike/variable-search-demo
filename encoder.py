import torch
import numpy as np
from pyserini.search import QueryEncoder
from sentence_transformers import SentenceTransformer


class SentenceTransformerEncoder(QueryEncoder):
    def __init__(self, model_name: str, device: str = 'cpu'):
        self.device = torch.device(device)
        self.model = SentenceTransformer(model_name, device=self.device)

    def encode(self, query: str):
        emb = self.model.encode(query)
        emb = emb / np.linalg.norm(emb)
        # emb = np.expand_dims(emb, axis=0)
        return emb