"""A piece of media with an audio track"""

import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List

import pytube
import pytube.streams
import requests

from .util import extract_video_id, get_temp_dir, remove_stop_words


class MediaContent(ABC):
    """A piece of media with an audio track"""

    source_url: str
    _slug: str = None

    def __init__(
        self,
        source_url: str,
    ) -> None:
        self.source_url = source_url

    @property
    @abstractmethod
    def title(self) -> str:
        """Get the event title

        :return: the event title
        :rtype: str
        """

    @property
    @abstractmethod
    def creator(self) -> str:
        """Get the event creator

        :return: the event creator
        :rtype: str
        """

    @property
    @abstractmethod
    def audio_url(self) -> str:
        """Get the URL to the audio file

        :return: URL of the audio file
        :rtype: str
        """

    @property
    @abstractmethod
    def audio_file(self) -> str:
        """Get the path to the audio file

        :return: file system path to audio file
        :rtype: str
        """

    @property
    @abstractmethod
    def media_key(self) -> str:
        """Get the unique identifier for the media content

        :return: media content's unique identifier
        :rtype: str
        """

    @property
    @abstractmethod
    def media_metadata(self) -> List[Dict[str, str]]:
        """Get the content metadata

        :return: List of dictionaries. The contents of the dictionary depends on the media type
        :rtype: List[Dict[str, str]]
        """

    @property
    @abstractmethod
    def s3_folder(self) -> str:
        """Get the s3 folder for this particular media type

        :return: the folder name
        :rtype: str
        """

    @property
    @abstractmethod
    def html_template(self) -> str:
        """Get the filename of the template to use

        :return: the template filename
        :rtype: str
        """

    @property
    def s3_path(self) -> str:
        """Get the s3 path to store the HTML file

        :return: the s3 path
        :rtype: str
        """
        return f"{self.s3_folder}/{self.slug}"

    @property
    def slug(self) -> str:
        """Generate a slug for this media suitable for a URL

        The slug consists of the timestamp when the slug was generated,
        the media identifier (if appropriate), and the title with stop words
        removed. Elements of the slug are separated by dashes.

        :return: the media slug
        :rtype: str
        """
        if self._slug is None:
            slug_elements = [datetime.now().strftime("%Y%m%dT%H%M%S")]
            if self.media_key:
                slug_elements.append(self.media_key)
            title_cleaned = re.sub(r"[^\w\s]", "", self.title)
            title_words = title_cleaned.lower().split()
            slug_elements.extend(remove_stop_words(title_words))
            _slug = "-".join(slug_elements)
        return _slug


class PodcastEpisode(MediaContent):
    """A podcast episode"""

    _title: str = None
    _creator: str = None
    _episode_url: str = None
    _audio_file: str = None

    def __init__(
        self,
        audio_url: str,
        episode_title: str,
        episode_url: str,
        podcast_title: str,
    ) -> None:  # noqa: N801
        super().__init__(source_url=audio_url)
        self._title = episode_title
        self._creator = podcast_title
        self._episode_url = episode_url

    @property
    def title(self) -> str:
        return self._title

    @property
    def creator(self) -> str:
        return self._creator

    @property
    def audio_url(self):
        return self.source_url

    @property
    def audio_file(self) -> str:
        if self._audio_file is None:
            self._audio_file = os.path.join(get_temp_dir(), "audio.mp3")
            response = requests.get(self.audio_url, stream=True, timeout=10)
            response.raise_for_status()
            with open(self._audio_file, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        return self._audio_file

    @property
    def media_key(self) -> str:
        creator_cleaned = re.sub(r"[^\w\s]", "", self.creator)
        creator_words = creator_cleaned.lower().split()
        return "-".join(remove_stop_words(creator_words)) + "-"

    @property
    def media_metadata(self) -> List[Dict[str, str]]:
        metadata = {
            "episode_title": self._title,
            "podcast_title": self._creator,
            "episode_url": self._episode_url,
        }
        return metadata

    @property
    def s3_folder(self) -> str:
        return "unchecked-transcript"

    @property
    def html_template(self) -> str:
        return "podcast_template.html.j2"


class YouTubeVideo(MediaContent):
    """A YouTube audio file"""

    _title: str = None
    _creator: str = None
    youtube_id: str
    pytube_object: pytube.YouTube
    _audio_stream: pytube.streams.Stream = None
    _audio_file: str = None

    def __init__(
        self, source_url: str, title: str = None, creator: str = None
    ) -> None:
        super().__init__(source_url=source_url)
        self.youtube_id = extract_video_id(self.source_url)
        self.pytube_object = pytube.YouTube(source_url)
        self._title = title
        self._creator = creator

    @property
    def media_key(self) -> str:
        return self.youtube_id

    @property
    def title(self) -> str:
        if self._title is None:
            self._title = self.pytube_object.title
        return self._title

    @property
    def creator(self) -> str:
        if self._creator is None:
            self._creator = self.pytube_object.author
        return self._creator

    @property
    def audio_url(self) -> str:
        return self._get_audio_stream().url

    @property
    def audio_file(self) -> str:
        if self._audio_file is None:
            audio_stream = self._get_audio_stream()
            self._audio_file = audio_stream.download(get_temp_dir())
        return self._audio_file

    @property
    def s3_folder(self) -> str:
        return "annotated-video"

    @property
    def html_template(self) -> str:
        return "youtube_template.html.j2"

    @property
    def media_metadata(self) -> List[Dict[str, str]]:
        iframe_source = f"https://www.youtube.com/embed/{self.youtube_id}"
        iframe_source += "?enablejsapi=1&widgetid=1&start=0&name=me"

        metadata = {
            "video_id": self.youtube_id,
            "iframe_src": iframe_source,
            "video_title": self.title,
            "video_creator": self.creator,
        }
        return metadata

    def _get_audio_stream(self) -> pytube.streams.Stream:
        if self._audio_stream is None:
            self._audio_stream = self.pytube_object.streams.filter(
                mime_type="audio/mp4"
            ).first()
        return self._audio_stream
