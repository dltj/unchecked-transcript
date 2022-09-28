import json
import logging
import tempfile
import time

import requests

from . import aws_session, config

log = logging.getLogger()


def create_transcript(
    audio_file_url: str,
    folder: str,
    episode_key: str,
) -> str:
    temp_file = tempfile.NamedTemporaryFile()
    r_session = requests.Session()
    with r_session.get(audio_file_url, stream=True) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            temp_file.write(chunk)
    temp_file.flush()
    temp_file.seek(0)
    log.debug("Got file")

    s3 = aws_session.resource("s3")
    s3_object = s3.Object(config.bucket, f"{folder}audio.mp3")
    s3_object.upload_fileobj(temp_file)
    temp_file.close()
    log.debug("Put file to S3")

    transcriber = aws_session.client("transcribe")
    job = f"podcast-{episode_key}"[:200]
    media_uri = f"s3://{config.bucket}/{folder}audio.mp3"
    r = transcriber.start_transcription_job(
        TranscriptionJobName=job,
        LanguageCode="en-US",
        Media={"MediaFileUri": media_uri},
        OutputBucketName=config.bucket,
        OutputKey=f"{folder}transcript",
        Subtitles={
            "Formats": [
                "vtt",
            ],
            "OutputStartIndex": 1,
        },
    )

    while True:
        time.sleep(30)
        r = transcriber.get_transcription_job(TranscriptionJobName=job)
        if r["TranscriptionJob"]["TranscriptionJobStatus"] == "FAILED":
            raise Exception(r["TranscriptionJob"]["FailureReason"], r)
        if r["TranscriptionJob"]["TranscriptionJobStatus"] == "COMPLETED":
            break

    s3_object_acl = s3.ObjectAcl(config.bucket, f"{folder}transcript.vtt")
    response = s3_object_acl.put(ACL="public-read")
    log.debug(f"Set WebVTT public ACL: {response=}")

    s3_object = s3.Object(config.bucket, f"{folder}transcription-job.json")
    response = s3_object.put(
        Body=json.dumps(r, default=str),
        ContentType="application/json",
        ACL="private",
    )
    log.debug(f"Upload job data: {response=}")

    vtt_uri = r["TranscriptionJob"]["Subtitles"]["SubtitleFileUris"][0]
    return vtt_uri
