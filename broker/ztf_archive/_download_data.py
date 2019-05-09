#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""This module downloads sample ZTF alerts from the ZTF alerts archive."""

import tarfile
from glob import glob
from os import makedirs
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

FILE_DIR = Path(__file__).resolve().parent
DATA_DIR = FILE_DIR / 'data'
ALERT_LOG = DATA_DIR / 'alert_log.txt'
ZTF_URL = "https://ztf.uw.edu/alerts/public/"
makedirs(DATA_DIR, exist_ok=True)


def _get_local_alerts_list():
    """Return a list of ZTF alert files that have already been downloaded

    Files will have already been unzipped into DATA_DIR

    Returns:
        A list of ZTF alert file names
    """

    if not ALERT_LOG.exists():
        return []

    else:
        return np.loadtxt(ALERT_LOG, dtype='str')


def _get_remote_file_list():
    """Get a list of published ZTF alerts from the ZTF Alert Archive

    Returns:
        A list of file names for alerts published on the ZTF archive
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


def _download_alerts_file(url, out_path):
    """Download a daily alerts file and unzip the contents

    Args:
        url      (str): URL of the file to download
        out_path (str): The path where the downloaded file should be written
    """

    out_dir = Path(out_path).parent
    if not out_dir.exists():
        makedirs(out_dir)

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
    with NamedTemporaryFile() as ofile:
        for data in data_iterable:
            ofile.write(data)

        tqdm.write('Unzipping alert data...')
        with tarfile.open(ofile.name, "r:gz") as data:
            data.extractall(out_dir)


def download_data(max_downloads=1):
    """Download recent alert data from the ZTF alerts archive

    Automatically skip published alerts that are empty. More recent releases
    are downloaded first. Skip releases that are already downloaded.

    Args:
        max_downloads (int): Number of daily releases to download (default = 1)
    """

    file_list = _get_remote_file_list()
    num_downloads = min(max_downloads, len(file_list))
    for i, file_name in enumerate(file_list):
        if i + 1 > max_downloads:
            break

        # Skip download if data was already downloaded
        if file_name in _get_local_alerts_list():
            tqdm.write(
                f'Already Downloaded ({i + 1}/{num_downloads}): {file_name}')
            continue

        out_path = DATA_DIR / file_name
        tqdm.write(f'Downloading ({i + 1}/{num_downloads}): {file_name}')

        url = requests.compat.urljoin(ZTF_URL, file_name)
        _download_alerts_file(url, out_path)

        with open(ALERT_LOG, 'a') as ofile:
            ofile.write(file_name)


def get_number_local_alerts():
    """Return the number of locally available alerts

    Returns:
        The number of alerts downloaded to the local machine
    """

    path_pattern = DATA_DIR / '*.avro'
    return len(glob(path_pattern))


def get_number_local_releases():
    """Return the number of ZTF daily alert releases that have been downloaded

    Returns:
        The number of daily data releases downloaded to the local machine
    """

    local_alerts = _get_local_alerts_list()
    try:
        return len(local_alerts)

    except TypeError:
        return 1
