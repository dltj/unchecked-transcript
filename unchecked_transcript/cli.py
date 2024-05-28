#!/usr/bin/env python
# encoding: utf-8
"""Create dirty transcript from audio file."""

import json
import logging
import re
from datetime import datetime
from typing import Callable

import click
from omegaconf import OmegaConf

from unchecked_transcript import aws_session, config
from unchecked_transcript.mediacontent import YouTubeVideo
from unchecked_transcript.podcast_html import podcast_html
from unchecked_transcript.podcast_transcript import podcast_transcript
from unchecked_transcript.transcription import Transcription
from unchecked_transcript.upload_html import upload_html

log = logging.getLogger()


# Common options decorator
def common_options(func: Callable) -> Callable:
    """Decorator to add common options to Click commands."""

    @click.option("--verbose", is_flag=True, help="Enables verbose mode.")
    @click.option("--debug", is_flag=True, help="Enables debug mode.")
    def wrapper(*args, verbose: bool, debug: bool, **kwargs):
        # Configure logging level based on the options
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        elif verbose:
            logging.basicConfig(level=logging.INFO)
        else:
            logging.basicConfig(level=logging.WARNING)
        logging.getLogger("botocore").setLevel(logging.WARNING)
        logging.getLogger("boto3").setLevel(logging.WARNING)
        logging.getLogger("pytube").setLevel(logging.WARNING)

        return func(*args, **kwargs)

    return wrapper


@click.group()
def cli_group():
    """Main CLI group"""


# END OF Common options decorator


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


@cli_group.command()
@click.argument("url", type=str)
@click.option(
    "-t",
    "--title",
    help="Override the video title supplied by YouTube",
    type=str,
)
@click.option(
    "-c",
    "--channel",
    help="Override the video channel supplied by YouTube",
    type=str,
)
@click.option(
    "--stdout",
    is_flag=True,
    default=False,
    help="If set, output will be printed to stdout instead of uploading to S3.",
)
@common_options
def youtubevideo(
    url: str,
    title: str,
    channel: str,
    stdout: bool,
):
    """Create an HTML transcript page for a YouTube video."""
    OmegaConf.set_readonly(config, True)

    yt = YouTubeVideo(source_url=url, title=title, creator=channel)
    transcription = Transcription(yt)
    transcription_html = transcription.html()
    if stdout:
        print(transcription_html)
    else:
        url = upload_html(html_string=transcription_html, folder=yt.s3_path)
        click.echo(f"Transcript file uploaded to {url}")


if __name__ == "__main__":
    youtubevideo()  # pylint: disable=no-value-for-parameter
