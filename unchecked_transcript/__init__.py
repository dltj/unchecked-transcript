import logging

import boto3
from omegaconf import OmegaConf

log = logging.getLogger()
log.setLevel(logging.DEBUG)
config = OmegaConf.load("config.yml")
aws_session = boto3.Session(
    aws_access_key_id=config.aws_access_key_id,
    aws_secret_access_key=config.aws_secret_access_key,
    region_name=config.region_name,
)
