"""A Transcription"""

import time
from typing import Dict, List, Tuple, Union

import jinja2
import whisper

from unchecked_transcript.mediacontent import MediaContent

TranscriptEntry = Dict[str, Union[float, str]]


class Transcription:
    """A transcription"""

    _media_content: MediaContent
    _result = None

    def __init__(self, media_content: MediaContent) -> None:
        self._media_content = media_content

    def _whisper_results(self) -> dict:
        if self._result is None:
            model = whisper.load_model("base")
            self._result = model.transcribe(
                self._media_content.audio_file, language="en"
            )
        return self._result

    @property
    def text(self) -> str:
        """The plaintext transcript

        :return: plaintext transcript
        :rtype: str
        """
        return self._whisper_results()["text"]

    @property
    def segments(self) -> list:
        """The transcript segments

        The returned list is an ordered array of segments of the transcription. Each segment
        element is a dictionary with these keys:

        * start: the start time of the segement (float)
        * end: the end time of the segment (float)
        * text: the text content of the segment (str)


        :return: transcript elements
        :rtype: list
        """
        return self._whisper_results()["segments"]

    def condense_segments(
        self, min_length: float = 23.0
    ) -> Tuple[List[TranscriptEntry], List[float]]:
        """Condense the transcript entries to a minimum length

        :param min_length: minimum length, defaults to 23.0
        :type min_length: float, optional
        :return: _description_
        :rtype: Tuple[List[TranscriptEntry], List[float]]
        """
        condensed_transcript: List[TranscriptEntry] = []
        start_times: List[float] = []
        condensed_entry: TranscriptEntry = None

        for entry in self.segments:
            try:
                start = float(entry.get("start"))
                duration = float(entry.get("end") - start)
                text = entry.get("text", "")
            except ValueError:
                continue

            text = text.replace("\n", " ")

            if condensed_entry is None:
                condensed_entry = {
                    "start": start,
                    "start_display": time.strftime(
                        "%H:%M:%S",
                        time.gmtime(entry.get("start", 0)),
                    ),
                    "text": text,
                    "duration": duration,
                }
            else:
                condensed_entry["duration"] += duration
                condensed_entry["text"] += " " + text

            # If the length of the condensed entry is over the minimum length in seconds _or_
            # this is the last segment of the transcript, append the condensed entry to the list.
            if (
                condensed_entry.get("duration", 0) >= min_length
                or entry == self.segments[-1]
            ):
                condensed_start = condensed_entry.get("start", 0)
                start_times.append(condensed_start)

                condensed_transcript.append(condensed_entry)
                condensed_entry = None
        return condensed_transcript, start_times

    def html(self) -> str:
        """Render HTML page using Jinja2 template specified by MediaContent

        :return: the HTML page
        :rtype: str
        """
        jinja_env = jinja2.Environment(
            loader=jinja2.PackageLoader("unchecked_transcript"),
            autoescape=jinja2.select_autoescape(),
        )
        template = jinja_env.get_template("youtube_template.html.j2")

        media_metadata = self._media_content.media_metadata
        condensed_transcript, start_times = self.condense_segments()

        placeholders = {
            **media_metadata,
            "transcript": condensed_transcript,
            "start_times": f"[ {','.join(str(x) for x in start_times)} ]",
        }

        html = template.render(placeholders)
        return html
