#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""This module downloads sample ZTF alerts from the ZTF alerts archive."""

import os
import shutil
import tarfile
from glob import glob
from pathlib import Path
from tempfile import TemporaryFile

import numpy as np
import requests
from astropy.table import Table
from tqdm import tqdm

from ..utils import setup_log

FILE_DIR = Path(__file__).resolve().parent
DATA_DIR = FILE_DIR / 'data'
ALERT_LOG = DATA_DIR / 'alert_log.txt'
ZTF_URL = "https://ztf.uw.edu/alerts/public/"
DATA_DIR.mkdir(exist_ok=True, parents=True)

if 'RTD_BUILD' not in os.environ:
    from google.cloud import error_reporting, storage

    error_client = error_reporting.Client()
    log = setup_log('data_upload')


def get_remote_md5_table():
    """Get a list of published ZTF data releases from the ZTF Alerts Archive

    Returns:
        A list of file names for alerts published on the ZTF Alerts Archive
    """

    # Get MD5 values
    md5_url = requests.compat.urljoin(ZTF_URL, 'MD5SUMS')
    md5_table = requests.get(md5_url).content.decode()

    out_table = Table(
        names=['md5', 'file'],
        dtype=['U32', 'U1000'],
        rows=[row.split() for row in md5_table.split('\n')[:-1]])

    return out_table['file', 'md5']


def get_local_release_list():
    """Return a list of ZTF daily releases that have already been downloaded

    Returns:
        A list of downloaded files from the ZTF Alerts Archive
    """

    if not ALERT_LOG.exists():
        return []

    with open(ALERT_LOG, 'r') as ofile:
        return [line.strip() for line in ofile]


def get_local_alert_list(return_iter=False):
    """Return a list of alert ids for all downloaded alert data

    Args:
        return_iter (bool): Return an iterator instead of a list (Default: False)

    Returns:
        A list of alert ID values as ints
    """

    path_pattern = str(DATA_DIR / '*.avro')
    data_iter = (int(Path(f).stem) for f in glob(path_pattern))

    if return_iter:
        return data_iter

    else:
        return list(return_iter)


def _download_alerts_file(file_name, out_path):
    """Download a file from the ZTF Alerts Archive

    Args:
        file_name (str): Name of the file to download
        out_path  (str): The path where the downloaded file should be written
    """

    out_dir = Path(out_path).parent
    if not out_dir.exists():
        out_dir.makedir(existok=True, parents=True)

    # noinspection PyUnresolvedReferences
    url = requests.compat.urljoin(ZTF_URL, file_name)
    file_data = requests.get(url, stream=True)

    # Get size of data to be downloaded
    total_size = int(file_data.headers.get('content-length', 0))
    block_size = 1024
    iteration_number = np.ceil(total_size // block_size)

    # Construct progress bar iterable
    data_iterable = tqdm(
        file_data.iter_content(block_size),
        total=iteration_number,
        unit='KB',
        unit_scale=True)

    # write data to file
    with TemporaryFile() as ofile:
        for data in data_iterable:
            ofile.write(data)

        tqdm.write('Unzipping alert data...')
        ofile.seek(0)
        with tarfile.open(fileobj=ofile, mode="r:gz") as data:
            data.extractall(out_dir)

    with open(ALERT_LOG, 'a') as ofile:
        ofile.write(file_name)


def download_data_date(year, month, day):
    """Download ZTF alerts for a given date

    Does not skip releases that are were previously downloaded.

    Args:
        year  (int): The year of the data to download
        month (int): The month of the data to download
        day   (int): The day of the data to download
    """

    file_name = f'ztf_public_{year}{month:02d}{day:02d}.tar.gz'
    tqdm.write(f'Downloading {file_name}')

    out_path = DATA_DIR / file_name
    _download_alerts_file(file_name, out_path)


def download_recent_data(max_downloads=1, stop_on_exist=False):
    """Download recent alert data from the ZTF alerts archive

    Data is downloaded in reverse chronological order. Skip releases that are
    already downloaded.

    Args:
        max_downloads  (int): Number of daily releases to download (default: 1)
        stop_on_exist (bool): Exit when encountering an alert that is already
                               downloaded (Default: False)
    """

    file_names = get_remote_md5_table()['File']
    num_downloads = min(max_downloads, len(file_names))
    for i, f_name in enumerate(file_names):
        if i >= max_downloads:
            break

        # Skip download if data was already downloaded
        if f_name in get_local_release_list():
            tqdm.write(
                f'Already Downloaded ({i + 1}/{num_downloads}): {f_name}')

            if stop_on_exist:
                return

            continue

        out_path = DATA_DIR / f_name
        tqdm.write(f'Downloading ({i + 1}/{num_downloads}): {f_name}')
        _download_alerts_file(f_name, out_path)


def delete_local_data():
    """Delete any locally data downloaded fro the ZTF Public Alerts Archive"""

    shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(exist_ok=True, parents=True)


def create_ztf_sync_table(bucket_name=None, out_path=None, verbose=False):
    """Create a table for uploading ZTF releases to a GCP bucket

    Only include files not already present in the bucket

    Args:
        bucket_name (str): Name of the bucket to upload into
        out_path    (str): Optionally write table to a txt file
    """

    # Get new file urls to upload
    release_table = get_remote_md5_table()
    out_table = Table(release_table['md5'])

    # Get existing files
    if bucket_name:
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(bucket_name)
        existing_files = [blob.name for blob in bucket.list_blobs()]

        is_new = ~np.isin(release_table['file'], existing_files)
        release_table = release_table[is_new]

    files = release_table['file']
    if verbose:
        files = tqdm(files, desc='Requesting file sizes')

    # Get file sizes
    url_list, size_list = [], []
    for file_name in files:
        url = requests.compat.urljoin(ZTF_URL, file_name)
        file_size = requests.head(url).headers['Content-Length']
        url_list.append(url)
        size_list.append(file_size)

    out_table['url'] = url_list
    out_table['file_size'] = size_list

    if out_path:
        # Format for compatibility with GCP data transfer service
        out_table.meta['comments'] = ['TsvHttpData-1.0']
        out_table.write(
            out_path,
            format='ascii.no_header',
            delimiter='\t',
            overwrite=True,
            comment='')

    return out_table
