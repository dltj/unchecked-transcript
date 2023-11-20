#!/usr/bin/env python
# encoding: utf-8
"""Create dirty transcript from audio file."""

import json
import logging
import re
from datetime import datetime

import click
from omegaconf import OmegaConf

from unchecked_transcript import aws_session, config
from unchecked_transcript.podcast_html import podcast_html
from unchecked_transcript.podcast_transcript import podcast_transcript
from unchecked_transcript.upload_html import upload_html
from unchecked_transcript.youtube_html import extract_video_id, youtube_html

log = logging.getLogger()


def get_episode_key(episode_key: str) -> str:
    transcribe_datestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    episode_key = f"{transcribe_datestamp}-{episode_key}"
    episode_key = episode_key.translate(
        {ord(c): "-" for c in "!@#$%^&*()[]{};:,./<>?\\|`~-=_+"}
    )
    episode_key = episode_key.translate({ord(" "): "_"})
    return episode_key


def upload_metadata(episode_metadata: str, folder: str) -> None:
    s3 = aws_session.resource("s3")
    s3_object = s3.Object(config.bucket, f"{folder}metadata.json")
    response = s3_object.put(
        Body=json.dumps(episode_metadata, default=str),
        ContentType="application/json",
        ACL="private",
    )
    log.debug(f"Upload metadata: {response=}")


@click.command()
@click.argument("audio_url", type=str)
@click.argument("episode_title", type=str)
@click.argument("episode_url", type=str)
@click.argument("podcast_title", type=str)
def podcast(
    audio_url: str,
    episode_title: str,
    episode_url: str,
    podcast_title: str,
):
    episode_metadata = {
        "audio_url": audio_url,
        "episode_title": episode_title,
        "episode_url": episode_url,
        "podcast_title": podcast_title,
    }
    OmegaConf.set_readonly(config, True)

    episode_key = (
        f"{episode_metadata['podcast_title']}--"
        f"{episode_metadata['episode_title']}"
    )
    episode_key = get_episode_key(episode_key)
    episode_metadata["episode_key"] = episode_key

    folder = f"{config.podcast_base_folder}/{episode_key}/"
    folder = re.sub(r"[^a-zA-Z0-9-_.!*()/]", "", folder)[:1023]

    vtt_uri = podcast_transcript(audio_url, folder, episode_key)
    click.echo(vtt_uri)

    html_string = podcast_html(vtt_uri, episode_metadata)
    upload_html(html_string=html_string, folder=folder)

    upload_metadata(episode_metadata, folder)
    click.echo(f"https://{config.bucket}/{folder}index.html")


@click.command()
@click.argument("youtube_url", type=str)
@click.argument("video_title", type=str)
@click.argument("video_creator", type=str)
@click.option(
    "-l",
    "--lang",
    default="en_US,en",
    help="One or more langagues, comma-separated",
)
@click.option(
    "-f",
    "--fromlang",
    help="Translate from this language",
)
def youtubevideo(
    youtube_url: str,
    video_title: str,
    video_creator: str,
    lang: str,
    fromlang: str,
):
    episode_metadata = {
        "youtube_url": youtube_url,
        "video_title": video_title,
        "video_creator": video_creator,
    }
    OmegaConf.set_readonly(config, True)

    youtube_video_id = extract_video_id(youtube_url)
    episode_key = get_episode_key(f"{youtube_video_id}-{video_title}")
    episode_metadata["episode_key"] = episode_key

    folder = f"{config.youtube_base_folder}/{episode_key}/"
    html_string = youtube_html(episode_metadata, lang, fromlang)
    upload_html(html_string=html_string, folder=folder)

    upload_metadata(episode_metadata, folder)
    click.echo(f"https://{config.bucket}/{folder}index.html")


if __name__ == "__main__":
    youtubevideo()  # pylint: disable=no-value-for-parameter
