#!/usr/bin/env python2.7
# -*- coding: UTF-8 -*-

"""This module downloads sample ZTF alerts."""

import os

import numpy as np
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import tarfile

ZTF_URL = "https://ztf.uw.edu/alerts/public/"


def _get_file_list():
    """Get a list of published ZTF alerts from the ZTF Alert Archive"""

    page_source = str(requests.get(ZTF_URL).content)
    soup = BeautifulSoup(page_source, features='lxml')
    soup_table = soup.find("table", attrs={"id": "indexlist"})

    # Get table rows - Ignore first, heading row and second empty row
    data_rows = soup_table.find_all("tr")[2:-1]

    file_list = []
    for row in data_rows:
        dataset = [td.get_text() for td in row.find_all("td")]
        file_name = dataset[1]
        file_size = dataset[3]
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

    out_dir = os.path.basename(out_path)
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


def download_data(local_dir, max_files=float('inf')):
    """Downloads data files from a given url and unzip if it is a .tar.gz

    If check_local_names is provided, check if <out_dir>/<check_local_name[i]>
    exists first and don't download the file if it does.

    Args:
        local_dir (str): Directory to save files into
        max_files (int): Maximum number of files to download (optional)
    """

    file_list = _get_file_list()
    for i, file_name in enumerate(file_list):
        if i >= max_files:
            break

        out_path = os.path.join(local_dir, file_name)
        print(f'Downloading ({i + 1}/{len(file_list)}): {file_name}')

        if os.path.exists(out_path):
            print('File already exists')
            continue

        try:
            url = requests.compat.urljoin(ZTF_URL, file_name)
            _download_file(url, out_path)

        except KeyboardInterrupt:
            os.remove(out_path)


if __name__ == '__main__':
    download_data('./data')
