#!/usr/bin/env python
# encoding: utf-8
"""Create dirty transcript from audio file."""

import logging
from typing import Callable

import click
from omegaconf import OmegaConf

from unchecked_transcript import config
from unchecked_transcript.mediacontent import PodcastEpisode, YouTubeVideo
from unchecked_transcript.transcription import Transcription
from unchecked_transcript.upload_html import upload_html

log = logging.getLogger()


# Common options decorator
def common_options(func: Callable) -> Callable:
    """Decorator to add common options to Click commands."""

    @click.option("--verbose", is_flag=True, help="Enables verbose mode.")
    @click.option("--debug", is_flag=True, help="Enables debug mode.")
    @click.option(
        "--stdout",
        is_flag=True,
        default=False,
        help="If set, output will be printed to stdout instead of uploading to S3.",
    )
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


@cli_group.command()
@click.argument("audio_url", type=str)
@click.argument("episode_title", type=str)
@click.argument("episode_url", type=str)
@click.argument("podcast_title", type=str)
@common_options
def podcast(
    audio_url: str,
    episode_title: str,
    episode_url: str,
    podcast_title: str,
    stdout: bool,
):
    """Create an HTML transcript page for a podcast episode."""
    OmegaConf.set_readonly(config, True)
    podcastepisode = PodcastEpisode(
        audio_url=audio_url,
        episode_title=episode_title,
        episode_url=episode_url,
        podcast_title=podcast_title,
    )
    transcription = Transcription(podcastepisode)
    transcription_html = transcription.html()
    if stdout:
        print(transcription_html)
    else:
        url = upload_html(
            html_string=transcription_html, folder=podcastepisode.s3_path
        )
        click.echo(f"Transcript file uploaded to {url}")


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
    podcast()  # pylint: disable=no-value-for-parameter
