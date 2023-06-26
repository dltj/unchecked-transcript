import re
import time

from jinja2 import Environment, PackageLoader, select_autoescape
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> str:
    """
    Get YouTube Video ID from URL

    Based heavily on JavaScript version by Amit Agarwal
    https://www.labnol.org/code/19797-regex-youtube-id

    Parameters:
      url (str): URL of video

    Returns: YouTube Video ID string
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


def youtube_html(episode_metadata: dict, lang: str) -> str:

    condensed_transcript = []

    video_id = extract_video_id(episode_metadata["youtube_url"])
    # language may be passed as query string. ?lang=de
    # multiple comma seperated languages are acceptable i.e ?lang=en,de
    # if multiple language versions of subs exist first one will be used
    if lang:
        lang_list = lang.split(",")
    else:
        # find default available languages for transcript
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        except Exception as e:
            raise ValueError(f"Video not found: {e}") from e

        lang_list = [i.language_code for i in transcript_list]

        # default to English if it exists
        # apparently first language in list is used in get_transcript
        if "en" in lang_list:
            lang_list.insert(0, "en")

    try:
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, languages=lang_list
        )
    except Exception as e:
        raise ValueError(f"Video not found: {e}") from e

    condensed_entry = None
    start_times = []

    for entry in transcript:
        start = entry.get("start")
        text = entry.get("text", "")
        duration = entry.get("duration", 0)

        text = text.replace("\n", " ")

        try:
            duration = float(duration)
        except Exception:
            continue

        if condensed_entry is None:
            condensed_entry = {
                "start": start,
                "text": text,
                "duration": duration,
            }

        else:
            condensed_entry["duration"] += duration
            condensed_entry["text"] += " " + text

        if condensed_entry.get("duration", 0) >= 23:
            condensed_entry["start_display"] = time.strftime(
                "%H:%M:%S", time.gmtime(condensed_entry.get("start", 0))
            )

            s = condensed_entry.get("start", 0)
            start_times.append(s)

            condensed_transcript.append(condensed_entry)
            condensed_entry = None

        # last entry
        elif entry == transcript[-1]:
            condensed_entry["start_display"] = time.strftime(
                "%H:%M:%S", time.gmtime(condensed_entry.get("start", 0))
            )

            s = condensed_entry.get("start", 0)
            start_times.append(s)

            condensed_transcript.append(condensed_entry)

    source = "https://www.youtube.com/embed/"
    source += video_id
    source += "?enablejsapi=1"
    # source += '?enablejsapi=1&origin='
    # source += 'https://docdrop.org'
    source += "&widgetid=1"
    source += "&start=0&name=me"

    canonical_url = f"https://www.youtube.com/watch?v={video_id}"

    env = Environment(
        loader=PackageLoader("unchecked_transcript"),
        autoescape=select_autoescape(),
    )
    placeholders = {
        **episode_metadata,
        "transcript": condensed_transcript,
        "video_id": video_id,
        "start_times": f"[ {','.join(str(x) for x in start_times)} ]",
        "canonical_url": canonical_url,
        "iframe_src": source,
    }
    template = env.get_template("youtube_template.html.j2")
    return template.render(placeholders)
