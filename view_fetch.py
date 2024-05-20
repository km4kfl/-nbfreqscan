import pickle
import boto3
import pprint
import io

def get_boto3_s3_client(cred_file, region='us-east-2'):
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

def main(cred_path: str, bucket_name: str):
    s3c = get_boto3_s3_client(cred_path)
    print('fetching')
    
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

    try:
        with open('plot.s3.fetched', 'r') as fd:
            for line in fd.readlines():
                line = line.strip()
                s3_fetched.add(line)
    except FileNotFoundError:
        pass

    for node in resp['Contents']:
        key = node['Key']
        parts = key.split('-')
        ct = float(parts[1])
        s3_online.append((key, ct))
    
    s3_online.sort(key=lambda item: item[1])

    with open('plot', 'ab') as plot_fd:
        for key, _ in s3_online:
            if key in s3_fetched:
                continue

            data_fd = io.BytesIO()
            
            print('downloading', key)
            s3c.download_fileobj(bucket_name, key, data_fd)
            print('appending')
            data_fd.seek(0)

            try:
                while True:
                    pkg_entry = pickle.load(data_fd)
                    data = pkg_entry['data']
                    src_ndx = pkg_entry['src_ndx']
                    mt = data['time']
                    freq = data['freq']
                    b0 = data['b0']
                    b1 = data['b1']
                    print(mt, freq, b0, b1, src_ndx)
                    pickle.dump((
                        mt, freq, b0, b1, src_ndx
                    ), plot_fd)
            except EOFError:
                pass

            with open('plot.s3.fetched', 'a') as fd:
                fd.write(f'{key}\n')

if __name__ == '__main__':
    main('z:\\nbfreqscan\\s3sak.txt', 'radio248')