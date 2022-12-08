import os
import hashlib

from glob import glob
from io import BytesIO
import traceback


import requests
import imagehash

from PIL import Image, ImageOps

from tqdm.auto import tqdm

import config


import boto3

s3 = boto3.client('s3')


def map_progress(pool, seq, f):
    results = []

    with tqdm(total=len(seq)) as progress:
        futures = []

        for el in seq:
            future = pool.submit(f, el)
            future.add_done_callback(lambda p: progress.update())
            futures.append(future)

        for future in futures:
            result = future.result()
            results.append(result)

    return results


def calculate_phashes(image_stream):
    img = Image.open(image_stream)

    dhash = str(imagehash.dhash(img))
    phash = str(imagehash.phash(img))
    whash = str(imagehash.whash(img))

    return {
        "dhash": dhash,
        "phash": phash,
        "whash": whash,
    }


def calculate_hashes(image_bytes):
    stream = BytesIO(image_bytes)
    hashes = calculate_phashes(stream)

    md5 = hashlib.md5(image_bytes).hexdigest()
    hashes["md5"] = md5

    return hashes


def read_and_calculate_hashes(filename):
    with open(filename, 'rb') as f_in:
        content = f_in.read()
    h = calculate_hashes(content)
    return (filename, h)



def toloka_post(url_suffix, data):
    url = f'{config.host}/{url_suffix}'
    return requests.post(url, json=data, headers=config.headers)


def toloka_patch(url_suffix, data):
    url = f'{config.host}/{url_suffix}'
    return requests.patch(url, json=data, headers=config.headers)


def toloka_get(url_suffix, params=None):
    if params is None:
        params = {}

    url = f'{config.host}/{url_suffix}'
    return requests.get(url, params=params, headers=config.headers)




def download_image_and_calc_hashes(attachment):
    try:
        filename = 'images/%s' % attachment

        if os.path.exists(filename):
            print('%s already exist' % filename)
            _, h = read_and_calculate_hashes(filename)
            return attachment, h

        print('downloading %s...' % filename)

        image_url = f'api/v1/attachments/{attachment}/download'
        res = toloka_get(image_url)

        h = calculate_hashes(res.content)
        
        with open(filename, 'wb') as f_out:
            f_out.write(res.content)

        return (attachment, h)
    except OSError:
        traceback.print_exc()
        return (attachment, None)


def make_verdict(suite_id, accept: bool, comment: str):
    if accept == True:
        status = 'ACCEPTED'
    else:
        status = 'REJECTED'

    verdict_url = f'api/v1/assignments/{suite_id}'

    request_body = {
        'status': status,
        'public_comment': comment
    }

    resp = toloka_patch(verdict_url, request_body)    
    print(suite_id, status, comment)
    return resp


def accept(id):
    return make_verdict(id, accept=True, comment='good job')


def reject(id, comment):
    return make_verdict(id, accept=False, comment=comment)


def make_upload_thumbnail(pool_id, attachment):
    output = f'thumbnails/{attachment}.jpg'
    if os.path.exists(output):
        bucket_name = 'toloka-kitchenware'
        prefix = f'https://{bucket_name}.s3.eu-west-1.amazonaws.com/{pool_id}/thumbnails'
        return f'{prefix}/{attachment}.jpg'

    make_thumbnail(attachment)
    return upload_thumbnail_to_s3(pool_id, attachment)


def make_thumbnail(attachment):
    with Image.open(f'images/{attachment}') as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail((1000, 1000), resample=Image.Resampling.BILINEAR)

        output = f'thumbnails/{attachment}.jpg'

        if image.mode != 'RGB':
            image = image.convert('RGB')

        image.save(output, format='jpeg', quality=95)
        print(f'saved a thumbnail to {output}')
        return output


def upload_thumbnail_to_s3(pool_id, attachment):
    thumbnail_path = f'thumbnails/{attachment}.jpg'
    key = f'{pool_id}/{thumbnail_path}'

    bucket_name = 'toloka-kitchenware'
    s3.upload_file(
        Filename=thumbnail_path,
        Bucket=bucket_name,
        Key=key
    )

    prefix = f'https://{bucket_name}.s3.eu-west-1.amazonaws.com/{pool_id}/thumbnails'
    image_url = f'{prefix}/{attachment}.jpg'
    return image_url

