#!/usr/bin/env python
# encoding: utf-8
"""Create dirty transcript from audio file."""

import click

from .create_transcript import create_transcript


@click.command()
@click.argument("audio_file", type=str)
def cli(audio_file: str):
    create_transcript(audio_file)
