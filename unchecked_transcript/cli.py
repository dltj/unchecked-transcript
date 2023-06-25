#!/usr/bin/env python
# encoding: utf-8
"""Create dirty transcript from audio file."""

import json
import logging
from datetime import datetime

import click
from omegaconf import OmegaConf

from . import aws_session, config
from .podcast_html import podcast_html
from .podcast_transcript import podcast_transcript
from .upload_html import upload_html

log = logging.getLogger()


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

    transcribe_datestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    episode_key = (
        f"{transcribe_datestamp}-"
        f"{episode_metadata['podcast_title']}--"
        f"{episode_metadata['episode_title']}"
    )
    episode_key = episode_key.translate(
        {ord(c): "-" for c in "!@#$%^&*()[]{};:,./<>?\\|`~-=_+"}
    )
    episode_key = episode_key.translate({ord(" "): "_"})
    episode_metadata["episode_key"] = episode_key

    folder = f"{config.base_folder}/{episode_key}/"

    vtt_uri = podcast_transcript(audio_url, folder, episode_key)
    click.echo(vtt_uri)

    html_string = podcast_html(vtt_uri, episode_metadata)
    upload_html(html_string=html_string, folder=folder)

    s3 = aws_session.resource("s3")
    s3_object = s3.Object(config.bucket, f"{folder}metadata.json")
    response = s3_object.put(
        Body=json.dumps(episode_metadata, default=str),
        ContentType="application/json",
        ACL="private",
    )
    log.debug(f"Upload metadata: {response=}")
    click.echo(f"https://{config.bucket}/{folder}index.html")


# if __name__ == "__main__":
#     cli(argv[1], argv[2])  # pylint: disable=no-value-for-parameter
