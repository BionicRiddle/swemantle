# gensim monkeypatch
import collections.abc

collections.Mapping = collections.abc.Mapping

from functools import partial
import pickle

import gensim.models.keyedvectors as word2vec

import math

import heapq
import json

import os

from numpy import dot
from numpy.linalg import norm

import re
import tqdm.contrib.concurrent

from hashlib import sha1

import code, traceback, signal

# check against all words + phrases in model?
ALL_WORDS = False


model = word2vec.KeyedVectors.load_word2vec_format(
    "../swectors-300dim.vec", binary=False
)


def make_words():
    words = []
    for word in model.key_to_index:
        words.append(word)

    return words


words = make_words()


def debug(sig, frame):
    """Interrupt running process, and provide a python prompt for
    interactive debugging."""
    d = {"_frame": frame}  # Allow access to frame object.
    d.update(frame.f_globals)  # Unless shadowed by global
    d.update(frame.f_locals)

    i = code.InteractiveConsole(d)
    message = "Signal received : entering python shell.\nTraceback:\n"
    message += "".join(traceback.format_stack(frame))
    i.interact(message)


def find_hints(secret, progress=True):
    if progress:  # works poorly in parellel
        worditer = tqdm.tqdm(words, leave=False)
    else:
        worditer = words

    target_vec = model[secret]
    target_vec_norm = norm(target_vec)

    #        syns = synonyms.get(secret) or []
    nearest = []
    reg = re.compile(".*\d.*")

    for word in worditer:
        vec = model[word]
        # why not model.wv.similarity(wordA, wordB)?
        similarity = dot(vec, target_vec) / (norm(vec) * target_vec_norm)
        heapq.heappush(nearest, (similarity, word))
        if len(nearest) > 1000 or reg.match(word):
            heapq.heappop(nearest)
    nearest.sort()
    return secret, nearest


if __name__ == "__main__":
    signal.signal(signal.SIGUSR1, debug)  # Register handler

    # synonyms = {}

    # with open("moby/words.txt") as moby:
    #     for line in moby.readlines():
    #         line = line.strip()
    #         words = line.split(",")
    #         word = words[0]
    #         synonyms[word] = set(words)

    print("loaded moby...")

    hints = {}

    secrets = []  # to have length for progress bar

    with open("static/assets/js/secretWords.js", encoding="utf-8") as f:
        for line in f.readlines():
            line = line.strip()
            if not '"' in line:
                continue
            secrets.append(line.strip('",'))

    CONCURRENCY = True
    if CONCURRENCY:
        # may need to limit concurrency for memory reasons
        # XXX bug: wraps all results into a list, e.g. won't write any until the very end
        mapper = tqdm.contrib.concurrent.process_map(
            partial(find_hints, progress=False),
            secrets,
            max_workers=(os.cpu_count() + 4),
            chunksize=1,
            total=len(secrets),
        )
    else:
        mapper = tqdm.tqdm(
            (find_hints(secret) for secret in secrets), total=len(secrets)
        )

    with open("hints.json", "w+") as hints_file:
        for secret, nearest in mapper:
            nearest = [(float(score), word) for score, word in nearest]
            hints_file.write(json.dumps({"word": secret, "neighbors": nearest}))
            hints_file.write("\n")
            hints_file.flush()
            hints[secret] = nearest

    with open(b"nearest.pickle", "wb") as f:
        pickle.dump(hints, f)
