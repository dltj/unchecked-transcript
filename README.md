# unchecked-transcript: Create an HTML page of transcript from an audio file

## Usage

poetry run transcript <AUDIO_URL> <EPISODE_TITLE> <EPISODE_URL> <PODCAST_TITLE>

poetry run youtube [--channel "Channel Name"] [--title "Video Title"] <YOUTUBE_URL> <VIDEO_TITLE> <VIDEO_CREATOR>

Be sure to quote each command line parameter if they have shell glob characters (e.g. '?' or '[').
For YouTube videos, `--channel` and/or `--title` can be used to override the data supplied by YouTube.

## Configuration

Create a `config.yml` file with these lines

```yaml
aws_access_key_id: <an AWS access key>
aws_secret_access_key: <corresponding secret key>
region_name: <valid AWS region name, e.g. 'us-east-1'>
bucket: <S3 bucket with Static Website Hosting turned on>
podcast_base_folder: <a folder under which the transcripts will be put>
youtube_base_folder: <a folder under which the YouTube annotation pages will be put>
```

## IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "VisualEditor0",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObjectAcl",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:PutObjectAcl"
      ],
      "Resource": [
        "arn:aws:s3:::media.dltj.org/annotated-video/*",
        "arn:aws:s3:::media.dltj.org/unchecked-transcript/*",
        "arn:aws:s3:::media.dltj.org"
      ]
    },
    {
      "Sid": "MultipartUploads",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucketMultipartUploads",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts"
      ],
      "Resource": [
        "arn:aws:s3:::media.dltj.org/annotated-video/*",
        "arn:aws:s3:::media.dltj.org/unchecked-transcript/*",
        "arn:aws:s3:::media.dltj.org"
      ]
    },
    {
      "Sid": "StartListTranscriptionJobs",
      "Effect": "Allow",
      "Action": [
        "transcribe:StartTranscriptionJob",
        "transcribe:ListTranscriptionJobs"
      ],
      "Resource": "*"
    },
    {
      "Sid": "GetTranscriptionJob",
      "Effect": "Allow",
      "Action": ["transcribe:GetTranscriptionJob"],
      "Resource": [
        "arn:aws:transcribe:us-east-1:<aws-account-id>:transcription-job/podcast*"
      ]
    }
  ]
}
```

## YouTube bot override

In 2024 and 2025, YouTube implemented some fairly rigorous bot detection.
[Issue 209](https://github.com/JuanBindez/pytubefix/pull/209) of the Python pytubefix library has the details, but the practical upshot is that a Node script is now required to get tokens from a YouTube player to get data.
Run `npm install youtube-po-token-generator` to get the prerequisites set up for the Node script.
