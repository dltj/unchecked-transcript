"""Utility functions"""

import atexit
import re
import shutil
import tempfile
from typing import List

# Create a temporary directory
TEMP_DIR = tempfile.mkdtemp()

STOP_WORDS = [
    "a",
    "an",
    "the",
    "and",
    "but",
    "or",
    "nor",
    "for",
    "so",
    "yet",
    "at",
    "by",
    "in",
    "on",
    "to",
    "from",
    "of",
    "with",
    "as",
    "if",
    "when",
    "than",
    "because",
    "where",
    "be",
    "am",
    "is",
    "are",
    "was",
    "were",
    "been",
    "being",
    "have",
    "has",
    "had",
    "having",
    "do",
    "does",
    "did",
    "doing",
    "will",
    "would",
    "shall",
    "should",
    "can",
    "could",
    "may",
    "might",
    "must",
    "i",
    "me",
    "myself",
    "you",
    "your",
    "yours",
    "he",
    "him",
    "his",
    "she",
    "her",
    "hers",
    "it",
    "its",
    "we",
    "us",
    "they",
    "them",
    "their",
    "theirs",
    "that",
    "this",
    "all",
    "any",
    "both",
    "each",
    "few",
    "many",
]


def cleanup() -> None:
    """Remove the temporary directory"""
    shutil.rmtree(TEMP_DIR)


# Register cleanup function to be called on program exit
atexit.register(cleanup)


def get_temp_dir() -> str:
    """Get the temporary directory

    :return: the path to the temporary directory
    :rtype: str
    """
    return TEMP_DIR


def remove_stop_words(
    words: List[str], stop_words: List[str] = None
) -> List[str]:
    """Remove stopwords from a list of words

    :param words: list of words
    :type words: List[str]
    :param stop_words: optional list of stopwords to override default list
    :type stop_words: List[str]
    :return: list of words with stop words removed
    :rtype: List[str]
    """
    if stop_words is None:
        stop_words = STOP_WORDS
    return [word for word in words if word.lower() not in stop_words]


def extract_video_id(url: str) -> str:
    """
    Get YouTubeVideo Video ID from URL

    Based heavily on JavaScript version by Amit Agarwal
    https://www.labnol.org/code/19797-regex-youtube-id

    Parameters:
      url (str): URL of video

    Returns: YouTubeVideo Video ID string
    """

    regExp = re.compile(
        r"^.*((youtu.be\/)|(v\/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#\&\?]*).*"
    )
    match = regExp.match(url)
    if match and len(match.group(7)) == 11:
        return match[7]
    else:
        raise ValueError(
            f"Could not extract video ID, {match.group[7]} is not 11 characters long."
        )
