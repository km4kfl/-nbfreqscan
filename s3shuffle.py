"""Shuffles measurement data into Amazon AWS S3 storage.

Instead of writing the output to a file we send it to Amazon
S3 storage. This extends the `freqscanclient` module.

# Dependencies
There is currently only one third-party dependency.

## Amazon Boto Client
    This is the only third-party dependency. It enables
    the interface with Amazon S3.

    python3 -m pip install boto3
"""
import freqscanclient
import io
import time
import uuid
import pickle
import boto3

def get_boto3_s3_client(region='us-east-2'):
    with open('s3sak.txt', 'r') as fd:
        lines = list(fd.readlines())
        access_key = lines[0].strip()
        secret_access_key = lines[1].strip()

    # devtestuser:devtest

    c = boto3.client(
        service_name='s3',
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_access_key
    )

    return c


def main():
    s3c = get_boto3_s3_client()

    source = freqscanclient.execute('config.yaml')

    while True:
        pkg = io.BytesIO()

        newest = None
        oldest = None

        print('building package')
        for data, src_ndx in source:
            ts = data['time']

            if newest is None or ts > newest:
                newest = ts
            if oldest is None or ts < oldest:
                oldest = ts

            pickle.dump({
                'data': data,
                'src_ndx': src_ndx,
            }, pkg)

            print('pkgadd', data)

            if pkg.tell() > 1024 * 1024 * 4:
                break
        
        print('uploading package')
        pkg.seek(0)
        ct = time.time()
        uid = uuid.uuid4().hex
        pkg_key = f'{uid}-{ct}-{oldest}-{newest}'
        s3c.upload_fileobj(pkg, 'radio248', pkg_key)

if __name__ == '__main__':
    main()