# unchecked-transcript: Create an HTML page of transcript from an audio file

## Usage

poetry run transcript <AUDIO_URL> <EPISODE_TITLE> <EPISODE_URL> <PODCAST_TITLE>

poetry run youtube [--lang <languages>] [--fromlang <baselanguage>] <YOUTUBE_URL> <VIDEO_TITLE> <VIDEO_CREATOR>

Be sure to quote each command line parameter if they have shell glob characters (e.g. '?' or '[').
YouTube transcripts can be translated from a base language if the desired language is not available and YouTube supplies automated translations.
Use the `--fromlang` parameter to specify the base language and the `--lang` parameter to specify the desired language.

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
            "Action": [
                "transcribe:GetTranscriptionJob"
            ],
            "Resource": [
                "arn:aws:transcribe:us-east-1:<aws-account-id>:transcription-job/podcast*"
            ]
        }
    ]
}
```
