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
import os.path
import os
import queue
import threading

def get_boto3_s3_client(region='us-east-2'):
    """Get a Boto3 S3 client using the local credential
    file s3sak.txt and return it.
    """
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
    """The main entry point for the program if run standalone.
    """
    s3c = get_boto3_s3_client()

    source = freqscanclient.execute('config.yaml')

    q = queue.Queue()

    upload_worker_th = threading.Thread(
        target=upload_worker,
        args=(s3c, q),
        daemon=True
    )

    disk_worker_th = threading.Thread(
        target=disk_worker,
        args=(s3c,),
        daemon=True
    )

    upload_worker_th.start()
    disk_worker_th.start()

    while True:
        pkg = io.BytesIO()

        newest = None
        oldest = None

        print('building package', time.time())

        ist = time.time()

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

            if time.time() - ist > 3:
                ist = time.time()
                prog = pkg.tell() / (1024 * 1024 * 4) * 100.0
                print('package progress: %.02f' % prog)

            if pkg.tell() > 1024 * 1024 * 4:
                break
        
        print('package ready', time.time())
        
        # Save the buffer in the event it is needed because
        # s3c calls close on the BytesIO object rendering
        # it unusable.
        buf = pkg.getvalue()
        
        pkg.seek(0)
        ct = time.time()
        uid = uuid.uuid4().hex
        pkg_key = f'{uid}-{ct}-{oldest}-{newest}'

        q.put((pkg_key, pkg))

def upload_worker(s3c, q):
    """Upload items from queue to Amazon S3.

    The main thread sends item via the queue, these
    are uploaded, and if the upload fails for any
    reason the package is written out to disk.
    """
    while True:
        pkg_key, pkg = q.get()
        buf = pkg.getvalue()
        try:
            if q.qsize() > 6:
                raise Exception('queue size is too big forcing disk dump')
            print('[UP] uploading', pkg_key)
            s3c.upload_fileobj(pkg, 'radio248', pkg_key)
            print('[UP] upload successful')
        except Exception as e:
            print(e)
            print('[UP] dumped to disk', e)
            with open('s3.' + pkg_key, 'wb') as fd:
                fd.write(buf)

def disk_worker(s3c):
    """Upload items from disk to Amazon S3.

    Scan the disk on interval and locate S3 package
    that failed to upload the first time. Try to
    upload each package and on success delete the
    disk file.
    """
    while True:
        for node in os.listdir('.'):
            if not node.startswith('s3.'):
                continue

            pkg_key = node[3:]
            
            try:
                print('[DISK] uploading', node)
                with open(node, 'rb') as fd:
                    s3c.upload_fileobj(
                        fd, 
                        'radio248', 
                        pkg_key,
                        ExtraArgs={
                            'StorageClass': 'STANDARD',
                        }
                    )
                os.remove(node)          
            except Exception as e:
                print('[DISK]', e)
        
        print('[DISK] sleeping')
        time.sleep(30)

if __name__ == '__main__':
    main()