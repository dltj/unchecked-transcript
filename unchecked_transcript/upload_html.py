"""Upload HTML to S3"""

import logging

from . import aws_session, config

log = logging.getLogger()


def upload_html(html_string: str, folder: str) -> str:
    """Upload an HTML file to S3

    :param html_string: the HTML to upload
    :type html_string: str
    :param folder: the path to upload the file to
    :type folder: str
    :return: URL to the transcript file
    :rtype: str
    """
    s3 = aws_session.resource("s3")
    if not folder.endswith("/"):
        folder = folder + "/"

    full_path = f"{folder}index.html"
    s3_object = s3.Object(config.bucket, full_path)
    response = s3_object.put(
        Body=html_string,
        ACL="public-read",
        ContentType="text/html",
    )
    log.debug("Transcript put; response=%s", response)

    return f"https://{config.bucket}/{full_path}"
