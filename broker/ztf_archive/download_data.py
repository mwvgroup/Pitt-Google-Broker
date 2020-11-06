#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Downloads sample ZTF alerts from the ZTF alerts archive."""

import shutil
import tarfile
from tempfile import TemporaryFile
from typing import Iterable
from warnings import warn

import numpy as np
import requests
from astropy.table import Table
from tqdm import tqdm

from broker.ztf_archive._utils import get_ztf_data_dir

ZTF_URL = "https://ztf.uw.edu/alerts/public/"


def get_remote_md5_table() -> Table:
    """Get a list of published ZTF data releases from the ZTF Alerts Archive

    Returns:
        A list of file names for alerts published on the ZTF Alerts Archive
    """

    md5_url = requests.compat.urljoin(ZTF_URL, 'MD5SUMS')
    md5_table = requests.get(md5_url).content.decode()
    out_table = Table(
        names=['md5', 'file'],
        dtype=['U32', 'U1000'],
        rows=[row.split() for row in md5_table.split('\n')[:-1]])

    return out_table['file', 'md5']


def get_local_releases() -> Iterable[str]:
    """Return an iterable of ZTF daily releases that have already been downloaded

    Returns:
        An iterable of downloaded release dates from the ZTF Alerts Archive
    """

    return (p.name.lstrip('ztf_public_') for p in get_ztf_data_dir().glob('*'))


def get_local_alerts() -> Iterable[int]:
    """Return an iterable list of alert ids for all downloaded alert data
    
    Returns:
        An iterable of alert ID values as ints
    """

    return (int(p.stem) for p in get_ztf_data_dir().glob('*/*.avro'))


def _download_alerts_file(
        file_name: str,
        out_dir: str,
        block_size: int,
        verbose: bool = True) -> None:
    """Download a file from the ZTF Alerts Archive

    Args:
        file_name: Name of the file to download
        out_dir: The directory where the file should be downloaded to
        block_size: Block size to use for large files
        verbose: Display a progress bar
    """

    # noinspection PyUnresolvedReferences
    url = requests.compat.urljoin(ZTF_URL, file_name)
    file_data = requests.get(url, stream=True)

    # Get size of data to be downloaded
    total_size = int(file_data.headers.get('content-length', 0))
    iteration_number = np.ceil(total_size // block_size)

    # Construct progress bar iterable
    data_iterable = file_data.iter_content(block_size)
    if verbose:
        data_iterable = tqdm(
            data_iterable,
            total=iteration_number,
            unit='KB',
            unit_scale=True)

    # write data to file
    with TemporaryFile() as ofile:
        for data in data_iterable:
            ofile.write(data)

        if verbose:
            tqdm.write('Unzipping alert data...')

        ofile.seek(0)
        with tarfile.open(fileobj=ofile, mode="r:gz") as data:
            data.extractall(out_dir)


def download_data_date(
        year: int,
        month: int,
        day: int,
        block_size: int = 1024,
        verbose: bool = True) -> None:
    """Download ZTF alerts for a given date

    Does not skip releases that are were previously downloaded.

    Args:
        year: The year of the data to download
        month: The month of the data to download
        day: The day of the data to download
        block_size: Block size to use for large files (Default: 1024)
        verbose: Display a progress bar (Default: True)
    """

    file_name = f'ztf_public_{year}{month:02d}{day:02d}.tar.gz'
    out_dir = get_ztf_data_dir() / file_name.rstrip('.tar.gz')
    _download_alerts_file(file_name, out_dir, block_size, verbose)


def download_recent_data(
        max_downloads: int = 1,
        block_size: int = 1024,
        verbose: bool = True,
        stop_on_exist: bool = False) -> None:
    """Download recent alert data from the ZTF alerts archive

    Data is downloaded in reverse chronological order. Skip releases that are
    already downloaded.

    Args:
        max_downloads: Number of daily releases to download
        block_size: Block size to use for large file
        verbose: Display a progress bar
        stop_on_exist: Exit when encountering an alert that is already downloaded
    """

    file_names = get_remote_md5_table()['file']
    num_downloads = min(max_downloads, len(file_names))
    for i, f_name in enumerate(file_names):
        if i >= max_downloads:
            break

        # Skip download if data was already downloaded
        if f_name in list(get_local_releases()):
            tqdm.write(
                f'Already Downloaded ({i + 1}/{num_downloads}): {f_name}')

            if stop_on_exist:
                return

            continue

        out_dir = get_ztf_data_dir() / f_name.rstrip('.tar.gz')
        tqdm.write(f'Downloading ({i + 1}/{num_downloads}): {f_name}')
        _download_alerts_file(f_name, out_dir, block_size, verbose)


def delete_local_data() -> None:
    """Delete any locally data downloaded fro the ZTF Public Alerts Archive"""

    shutil.rmtree(get_ztf_data_dir())


def create_ztf_sync_table(
        out_path: str = None,
        bucket_name: str = None,
        verbose: bool = True) -> Table:
    """Create a table for uploading ZTF releases to a GCP bucket

    Only include files not already present in the bucket

    Args:
        out_path    (str): Optionally write table to a txt file
        bucket_name (str): Name of the bucket to upload into
        verbose    (bool): Whether to display a progress bar (Default: True)
    """

    from google.cloud import storage

    # Get new file urls to upload
    release_table = get_remote_md5_table()
    if bucket_name:
        bucket = storage.Client().get_bucket(bucket_name)
        existing_files = [blob.name for blob in bucket.list_blobs()]

        # Drop existing files from the release table
        is_new = ~np.isin(release_table['file'], existing_files)
        release_table = release_table[is_new]

    # Get file sizes
    url_list, size_list = [], []
    for file_name in tqdm(release_table['file'], desc='ZTF files', disable=not verbose):
        url = requests.compat.urljoin(ZTF_URL, file_name)
        file_size = float(requests.head(url).headers.get('Content-Length', -99))
        if file_size < 0:
            warn(f'No file size found for {file_name}')

        size_list.append(file_size)
        url_list.append(url)

    out_table = Table({'url': url_list, 'size': size_list, 'md5': release_table['md5']})
    out_table = out_table[out_table['size'] >= 0]

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
