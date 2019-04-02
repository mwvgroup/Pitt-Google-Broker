#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""This module downloads sample ZTF alerts archive."""

import os
import tarfile

import numpy as np
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(FILE_DIR, 'data')
ALERT_LOG = os.path.join(FILE_DIR, 'alert_log.txt')
ZTF_URL = "https://ztf.uw.edu/alerts/public/"
os.makedirs(DATA_DIR, exist_ok=True)


def _get_local_alerts_list():
    """Return a list of ZTF alert files that have already been downloaded

    Files will have already been unzipped into DATA_DIR

    Returns:
        A list of ZTF alert file names
    """

    if not os.path.exists(ALERT_LOG):
        return []

    else:
        return np.loadtxt(ALERT_LOG, dtype='str')


def _get_remote_file_list():
    """Get a list of published ZTF alerts from the ZTF Alert Archive

    returns:
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


def _download_file(url, out_path):
    """Download a specified file to a given output path

    Any top level .tar.gz archives will be automatically unzipped.

    Args:
        url      (str): URL of the file to download
        out_path (str): The path where the downloaded file should be written
    """

    out_dir = os.path.dirname(out_path)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

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
    with open(out_path, 'wb') as f:
        for data in data_iterable:
            f.write(data)

    print('Unzipping file...')
    if out_path.endswith(".tar.gz") or out_path.endswith(".tgz"):
        with tarfile.open(out_path, "r:gz") as data:
            data.extractall(out_dir)

        os.remove(out_path)


def download_data(max_downloads=1):
    """Downloads data files from a given url and unzip if it is a .tar.gz

    Does not skip data that is already downloaded. Skips published alerts that
    are empty.

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
            print(f'Already Downloaded ({i + 1}/{num_downloads}): {file_name}')
            continue

        out_path = os.path.join(DATA_DIR, file_name)
        print(f'Downloading ({i + 1}/{num_downloads}): {file_name}')

        try:
            url = requests.compat.urljoin(ZTF_URL, file_name)
            _download_file(url, out_path)

            with open(ALERT_LOG, 'a') as ofile:
                ofile.write(file_name)

        except KeyboardInterrupt:
            os.remove(out_path)
            return


def get_number_local_alerts():
    """Return the number of locally available alerts"""

    path_pattern = os.path.join(DATA_DIR, '*.avro')
    return len(glob(path_pattern))


def number_local_releases():
    """Return the number of ZTF daily alert releases that have been downloaded
    """

    local_alerts = _get_local_alerts_list()
    try:
        return len(local_alerts)

    except TypeError:
        return 1
