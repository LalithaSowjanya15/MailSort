"""
Rule-based extractive summarizer for MailSort.
"""

import math
import re

from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

from utils.helpers import logger


try:
    STOP_WORDS = set(stopwords.words("english"))
except Exception:
    STOP_WORDS = set()


PUNCT = re.compile(r"[^\w\s]")


def tokenize(text):

    cleaned = PUNCT.sub(" ", text.lower())

    try:
        words = word_tokenize(cleaned)
    except Exception:
        words = cleaned.split()

    return [
        w
        for w in words
        if w not in STOP_WORDS and len(w) > 1
    ]


def generate_summary(body, max_sentences=2):

    if not body.strip():
        return ""

    try:
        sentences = sent_tokenize(body)
    except Exception:
        sentences = [s.strip() for s in body.split("\n") if s.strip()]

    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    freq = {}

    for word in tokenize(body):
        freq[word] = freq.get(word, 0) + 1

    scores = []

    for i, sentence in enumerate(sentences):

        words = tokenize(sentence)

        score = sum(freq.get(w, 0) for w in words)

        if words:
            score /= math.log(len(words) + 1)

        scores.append((i, sentence, score))

    best = sorted(scores, key=lambda x: x[2], reverse=True)[:max_sentences]

    best.sort(key=lambda x: x[0])

    return " ".join([x[1] for x in best])