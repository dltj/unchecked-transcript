import logging

from . import aws_session, config

log = logging.getLogger()


def upload_html(html_string: str, folder: str) -> None:
    s3 = aws_session.resource("s3")
    s3_object = s3.Object(config.bucket, f"{folder}index.html")
    response = s3_object.put(
        Body=html_string,
        ACL="public-read",
        ContentType="text/html",
    )
    log.debug(f"Transcript put; {response=}")
