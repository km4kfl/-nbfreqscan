import pickle
import boto3
import pprint
import io

def get_boto3_s3_client(cred_file: str, region='us-east-2'):
    with open(cred_file, 'r') as fd:
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

def main(cred_path: str, bucket_name: str, data_path: str):
    s3c = get_boto3_s3_client(cred_path)

    start_after = None

    s3_online = []

    while True:    
        print('Fetching S3 index.')

        if start_after is None:
            resp = s3c.list_objects_v2(
                Bucket=bucket_name,
            )
        else:
            resp = s3c.list_objects_v2(
                Bucket=bucket_name,
                StartAfter=start_after
            )

        nodes = resp['Contents']

        for node in nodes:
            key = node['Key']
            parts = key.split('-')
            ct = float(parts[1])
            item = (key, ct)
            assert item not in s3_online
            s3_online.append((key, ct))

        if len(nodes) == 1000:
            print('Fetching remaining items.')
            start_after = nodes[-1]['Key']
        else:
            break

    print(f'Have index of {len(s3_online)} items.')

    s3_fetched = set()

    print('Scanning existing data to build index of downloaded bucket nodes..')
    try:
        with open(data_path, 'rb') as fd:
            try:
                while True:
                    s3_key, _ = pickle.load(fd)
                    s3_fetched.add('-'.join([str(v) for v in s3_key]))
            except EOFError:
                pass
    except FileNotFoundError:
        pass
    
    s3_online.sort(key=lambda item: item[1])

    with open(data_path, 'ab') as plot_fd:
        for key, _ in s3_online:
            if key in s3_fetched:
                print('skipped', key)
                continue

            data_fd = io.BytesIO()
            
            print('Downloading.', key)
            s3c.download_fileobj(bucket_name, key, data_fd)
            print('Appending.')
            data_fd.seek(0)

            key = key.split('-')
            key = (
                key[0],
                float(key[1]),
                float(key[2]),
                float(key[3]),
            )

            data = []
            try:
                while True:
                    item = pickle.load(data_fd)
                    data.append(item)
            except EOFError:
                pass

            pickle.dump((
                (key, data)
            ), plot_fd)

if __name__ == '__main__':
    main('z:\\nbfreqscan\\s3sak.txt', 'radio248', 's3radio248.pickle')