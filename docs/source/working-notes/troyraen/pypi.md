# PyPI setup for pgb-utils<a name="pypi-setup-for-pgb-utils"></a>

<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=1 -->

- [PyPI setup for pgb-utils](#pypi-setup-for-pgb-utils)
  - [Links](#links)
  - [Setup:](#setup)
  - [Build the distribution and upload it to testpypi](#build-the-distribution-and-upload-it-to-testpypi)
  - [Build the distribution and upload it to PyPI](#build-the-distribution-and-upload-it-to-pypi)
  - [Work in development ("editable") mode:](#work-in-development-editable-mode)

<!-- mdformat-toc end -->

## Links<a name="links"></a>

- [Packaging Python Projects](https://packaging.python.org/tutorials/packaging-projects/)
- [Packaging and distributing projects](https://packaging.python.org/guides/distributing-packages-using-setuptools/)
- [Example Project](https://github.com/pypa/sampleproject)
- [Working in “development mode”](https://packaging.python.org/guides/distributing-packages-using-setuptools/#working-in-development-mode)

## Setup:<a name="setup"></a>

```bash
pgbenv
python -m pip install --upgrade pip setuptools wheel
python -m pip install twine

python3 -m pip install --upgrade build
```

## Build the distribution and upload it to testpypi<a name="build-the-distribution-and-upload-it-to-testpypi"></a>

```bash
cd /Users/troyraen/Documents/PGB/repo/pgb_utils
python3 -m build
python3 -m twine upload --repository testpypi dist/*
```

View at: https://test.pypi.org/project/pgb-utils-alpha/0.0.1/

## Build the distribution and upload it to PyPI<a name="build-the-distribution-and-upload-it-to-pypi"></a>

```bash
cd /Users/troyraen/Documents/broker/repo2/pgb_utils
python3 -m build
python3 -m twine upload dist/*
```

View at: https://pypi.org/project/pgb-utils/0.1.0/

## Work in development ("editable") mode:<a name="work-in-development-editable-mode"></a>

```bash
conda create --name pgbutils python=3.7 pip ipython
conda activate pgbutils
export GOOGLE_APPLICATION_CREDENTIALS=/Users/troyraen/Documents/broker/repo/GCP_auth_key.json

cd /Users/troyraen/Documents/broker/repo2/pgb_utils
python -m pip install -e .
```

```python
import pgb_utils as pgb
```
