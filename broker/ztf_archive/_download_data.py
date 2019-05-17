#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""This module downloads sample ZTF alerts from the ZTF alerts archive."""

import tarfile
from glob import glob
from os import makedirs
from pathlib import Path
from tempfile import TemporaryFile

import numpy as np
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

FILE_DIR = Path(__file__).resolve().parent
DATA_DIR = FILE_DIR / 'data'
ALERT_LOG = DATA_DIR / 'alert_log.txt'
ZTF_URL = "https://ztf.uw.edu/alerts/public/"
makedirs(DATA_DIR, exist_ok=True)


def get_remote_release_list():
    """Get a list of published ZTF data releases from the ZTF Alerts Archive

    Returns:
        A list of file names for alerts published on the ZTF Alerts Archive
    """

    # Get html table from page source
    page_source = str(requests.get(ZTF_URL).content)
    soup = BeautifulSoup(page_source, features='lxml')
    soup_table = soup.find("table", attrs={"id": "indexlist"})

    # Get table rows with data - Ignore first header row. The second and last
    # rows are empty so are also ignored
    data_rows = soup_table.find_all("tr")[2:-1]

    # Create list of alert file names
    file_list = []
    for row in data_rows:
        row_data = [td.get_text() for td in row.find_all("td")]
        file_name = row_data[1]
        file_size = row_data[3]

        # Skip alerts that are empty
        if file_size.strip() != '44':
            file_list.append(file_name)

    return file_list


def get_local_release_list():
    """Return a list of ZTF daily releases that have already been downloaded

    Returns:
        A list of downloaded files from the ZTF Alerts Archive
    """

    if not ALERT_LOG.exists():
        return []

    with open(ALERT_LOG, 'r') as ofile:
        return [line.strip() for line in ofile]


def get_local_alert_list():
    """Return a list of alert ids for all downloaded alert data

    Returns:
        A list of alert ID values as ints
    """

    path_pattern = str(DATA_DIR / '*.avro')
    return [int(Path(f).with_suffix('').name) for f in glob(path_pattern)]


def _download_alerts_file(file_name, out_path):
    """Download a file from the ZTF Alerts Archive

    Args:
        file_name (str): Name of the file to download
        out_path  (str): The path where the downloaded file should be written
    """

    out_dir = Path(out_path).parent
    if not out_dir.exists():
        makedirs(out_dir)

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

    file_list = get_remote_release_list()
    num_downloads = min(max_downloads, len(file_list))
    for i, file_name in enumerate(file_list):
        if i >= max_downloads:
            break

        # Skip download if data was already downloaded
        if file_name in get_local_release_list():
            tqdm.write(
                f'Already Downloaded ({i + 1}/{num_downloads}): {file_name}')

            if stop_on_exist:
                return

            continue

        out_path = DATA_DIR / file_name
        tqdm.write(f'Downloading ({i + 1}/{num_downloads}): {file_name}')
        _download_alerts_file(file_name, out_path)
