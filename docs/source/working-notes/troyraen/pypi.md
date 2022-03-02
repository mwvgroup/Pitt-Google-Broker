# PyPI setup for pgb-utils

- [Packaging Python Projects](https://packaging.python.org/tutorials/packaging-projects/)
- [Packaging and distributing projects](https://packaging.python.org/guides/distributing-packages-using-setuptools/)
- [Example Project](https://github.com/pypa/sampleproject)
- [Working in “development mode”](https://packaging.python.org/guides/distributing-packages-using-setuptools/#working-in-development-mode)

## Setup:

```bash
pgbenv
python -m pip install --upgrade pip setuptools wheel
python -m pip install twine

python3 -m pip install --upgrade build
```

## Build the distribution and upload it to testpypi

```bash
cd /Users/troyraen/Documents/PGB/repo/pgb_utils
python3 -m build
python3 -m twine upload --repository testpypi dist/*
```

View at: https://test.pypi.org/project/pgb-utils-alpha/0.0.1/

## Build the distribution and upload it to PyPI

```bash
cd /Users/troyraen/Documents/broker/repo2/pgb_utils
python3 -m build
python3 -m twine upload dist/*
```

View at: https://pypi.org/project/pgb-utils/0.1.0/

## Work in development ("editable") mode:

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
