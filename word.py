from typing import List
from main import EMBED_TEMPLATE

class Word:
    def __init__(self, word: str = None, url: str = None, extras: List[str] = None):
        self._word = word
        self._url = url
        self._extras = extras

    def __copy__(self):
        return Word(self._word, self.url, self._extras)

    def __eq__(self, other):
        return other and self._word == other.word and self._url == other.url

    def __str__(self):
        return "{} [{}]: {}".format(self._word, self._url, self._extras)

    @property
    def word(self):
        return self._word

    @word.setter
    def word(self, word):
        if self._word:
            raise RuntimeError("Cannot override word. Make a new Word.")
        self._word = word

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        if self._url:
            raise RuntimeError("Cannot override URL. Make a new Word.")
        self._url = url

    @property
    def extras(self):
        return self._extras

    @extras.setter
    def extras(self, extras: List[str]):
        self._extras = extras

    def to_embed(self):
        e = EMBED_TEMPLATE()
        e.add_field(name="Word", value="[{}]({})".format(self._word, self._url))
        meaning_value = "\n".join(self._extras)
        e.add_field(name="Meaning", value=meaning_value)
        return e
