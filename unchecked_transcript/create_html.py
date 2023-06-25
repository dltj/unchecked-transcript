from io import StringIO

import requests
import spacy
import webvtt
from jinja2 import Environment, PackageLoader, select_autoescape


def create_html(vtt_file: str, episode_metadata: dict) -> str:
    # Get the WebVTT file
    r = requests.get(vtt_file)
    r.raise_for_status()
    buffer = StringIO(r.text)
    vtt = webvtt.read_buffer(buffer)

    # Build up the transcript into a single string
    transcript = ""
    for line in vtt:
        transcript += line.text + " "

    # Load the transcript into nlp for sentence splitting
    nlp = spacy.load("en_core_web_lg")
    doc = nlp(transcript)

    timed_text = []
    vtt_counter = 0
    text_start_time = None
    saved_sentence = ""
    for sentence in doc.sents:
        for index in range(vtt_counter, min(len(vtt), vtt_counter + 50)):
            if sentence.text.startswith(vtt[index].text):
                # Appending is skipped the first time through the loop
                if text_start_time:
                    timed_text.append(
                        {
                            "start_time": text_start_time.split(".", 1)[0],
                            "sentence": saved_sentence,
                        }
                    )
                text_start_time = vtt[index].start
                saved_sentence = sentence.text
                vtt_counter = index + 1
                break
        else:
            saved_sentence += " " + sentence.text
    # Save the last sentence
    timed_text.append(
        {
            "text_start_time": text_start_time,
            "sentence": saved_sentence,
        }
    )

    env = Environment(
        loader=PackageLoader("unchecked_transcript"),
        autoescape=select_autoescape(),
    )
    placeholders = {**episode_metadata, "timed_text": timed_text}
    template = env.get_template("podcast_template.html.j2")
    return template.render(placeholders)
