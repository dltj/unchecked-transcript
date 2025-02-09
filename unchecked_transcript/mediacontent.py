"""A piece of media with an audio track"""

import json
import logging
import os
import re
import subprocess
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Tuple

import pytubefix
import requests

from .util import extract_video_id, get_temp_dir, remove_stop_words

log = logging.getLogger()


def _generate_youtube_tokens() -> Tuple[str, str]:
    command = "node scripts/youtube-token-generator.js"
    try:
        shell_result = subprocess.run(
            command,
            check=True,
            shell=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        log.critical(f"{command} STDOUT: {error.stdout}\n")
        log.critical(f"{command} STDERR: {error.stderr}\n")
        sys.exit(1)
    token_object = json.loads(shell_result.stdout)
    log.debug(f"Result: {token_object=}")
    return token_object["visitorData"], token_object["poToken"]


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
    def text(self) -> list:
        """Get any predefined text

        Returns:
            list: long string
        """

    @property
    @abstractmethod
    def segments(self) -> list:
        """Get any predefined captions

        Returns:
            list: caption list
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
            self._slug = "-".join(slug_elements)
        return self._slug


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
    def text(self):
        return None

    @property
    def segments(self) -> list:
        return None

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
    pytube_object: pytubefix.YouTube
    _audio_stream: pytubefix.streams.Stream = None
    _audio_file: str = None

    def __init__(
        self, source_url: str, title: str = None, creator: str = None
    ) -> None:
        super().__init__(source_url=source_url)
        self.youtube_id = extract_video_id(self.source_url)
        self.pytube_object = pytubefix.YouTube(
            source_url,
            client="WEB",
            use_po_token=True,
            po_token_verifier=_generate_youtube_tokens,
        )
        self._title = title
        self._creator = creator

    @staticmethod
    def _convert_to_seconds(time_str):
        """
        Converts a time string from SRT format (hh:mm:ss,ms) to seconds.

        This function parses a time string from the SRT format, splitting into
        hours, minutes, seconds, and milliseconds, and converts it into a floating
        point number representing the equivalent time in seconds.

        Args:
            time_str (str): Time string in the format "hh:mm:ss,ms".

        Returns:
            float: The time in seconds.

        Example:
            seconds = convert_to_seconds("00:00:10,160")
            # Output: 10.16
        """
        hours, minutes, seconds_ms = time_str.split(":")
        seconds, milliseconds = seconds_ms.split(",")
        return (
            int(hours) * 3600
            + int(minutes) * 60
            + int(seconds)
            + int(milliseconds) / 1000.0
        )

    def _parse_srt(self, lang="en"):
        """
        Parses SRT (SubRip Subtitle) contents into a list of subtitle entries.

        Each entry in the returned list is a dictionary containing the start time,
        end time, and text of the subtitle. The times are converted to seconds with
        milliseconds.

        Args:
            srt_content (str): The content of the SRT file as a string.

        Returns:
            list: A list of dictionaries, each with 'start' (float), 'end' (float),
                and 'text' (str) keys representing the timecoded subtitle entries.

        Example:
            srt_content = \"\"\"
            1
            00:00:10,160 --> 00:00:19,360
            Example subtitle text.

            2
            00:00:19,360 --> 00:00:26,480
            Another subtitle entry.
            \"\"\"
            result = parse_srt(srt_content)
            # Output: [{'start': 10.16, 'end': 19.36, 'text': 'Example subtitle text.'}, ...]

        """
        subtitles = []
        srt_content = self.pytube_object.captions[lang].generate_srt_captions()
        blocks = srt_content.strip().split(
            "\n\n"
        )  # Split the input into blocks

        for block in blocks:
            lines = block.split("\n")
            if len(lines) >= 3:
                _, timecode, *text = lines
                start_str, end_str = map(str.strip, timecode.split("-->"))

                start_seconds = self._convert_to_seconds(start_str)
                end_seconds = self._convert_to_seconds(end_str)
                text_content = " ".join(text).strip()

                subtitle = {
                    "start": start_seconds,
                    "end": end_seconds,
                    "text": text_content,
                }
                subtitles.append(subtitle)

        return subtitles

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
    def text(self):
        if self.segments:
            only_text = "\n".join([x.text for x in self.segments])
            return only_text
        return None

    @property
    def segments(self) -> list:
        if "en" in self.pytube_object.captions:
            return self._parse_srt("en")
        if "en-US" in self.pytube_object.captions:
            return self._parse_srt("en-US")
        if "en-GB" in self.pytube_object.captions:
            return self._parse_srt("en-GB")
        return None

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

    def _get_audio_stream(self) -> pytubefix.streams.Stream:
        if self._audio_stream is None:
            self._audio_stream = self.pytube_object.streams.filter(
                mime_type="audio/mp4"
            ).first()
        return self._audio_stream
