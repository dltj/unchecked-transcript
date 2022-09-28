# unchecked-transcript: Create an HTML page of transcript from an audio file

## Usage

poetry run transcript <AUDIO_URL> <EPISODE_TITLE> <EPISODE_URL> <PODCAST_TITLE>

Be sure to quote each command line parameter if they have shell glob characters (e.g. '?' or '[')

## Configuration
Create a `config.yml` file with these lines

```yaml
aws_access_key_id: <an AWS access key>
aws_secret_access_key: <corresponding secret key>
region_name: <valid AWS region name, e.g. 'us-east-1'>
bucket: <S3 bucket with Static Website Hosting turned on>
base_folder: <a folder under which the transcripts will be put>
```
