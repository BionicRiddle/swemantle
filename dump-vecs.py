# gensim monkeypatch
import collections.abc

collections.Mapping = collections.abc.Mapping

import gensim.models.keyedvectors as word2vec
import numpy as np

import sqlite3
import tqdm

from more_itertools import chunked

model = word2vec.KeyedVectors.load_word2vec_format("../swectors-300dim.vec", binary=False)

con = sqlite3.connect("word2vec.db")
con.execute("PRAGMA journal_mode=WAL")
cur = con.cursor()
cur.execute("""create table if not exists word2vec (word text PRIMARY KEY, vec blob)""")
con.commit()

# import pdb;pdb.set_trace()

CHUNK_SIZE = 1111
con.execute("DELETE FROM word2vec")
for words in chunked(tqdm.tqdm(model.key_to_index), CHUNK_SIZE):
    with con:
        con.executemany(
            "insert into word2vec values(?,?)",
            ((word, model[word].tobytes()) for word in words),
        )
