# docs/source/working-notes/troyraen/v0.4.0/pypi.md

## PyPI setup for pgb-utils

- [Packaging Python Projects](https://packaging.python.org/tutorials/packaging-projects/)
- [Packaging and distributing projects](https://packaging.python.org/guides/distributing-packages-using-setuptools/)
- [Example Project](https://github.com/pypa/sampleproject)
- [Working in “development mode”](https://packaging.python.org/guides/distributing-packages-using-setuptools/#working-in-development-mode)

### Setup:
```bash
pgbenv
python -m pip install --upgrade pip setuptools wheel
python -m pip install twine

python3 -m pip install --upgrade build
```

### Build the distribution and upload it to testpypi
```bash
cd /Users/troyraen/Documents/PGB/repotest/broker/broker_utils
python3 -m build
python3 -m twine upload --repository testpypi dist/*
```

View at: https://test.pypi.org/project/pgb-broker-utils

Install with: `python3 -m pip install --index-url https://test.pypi.org/simple/ --no-deps pgb_broker_utils`

### Build the distribution and upload it to PyPI
```bash
cd /Users/troyraen/Documents/PGB/repo3/broker/broker_utils
python3 -m build
python3 -m twine upload dist/*
```
View at: https://pypi.org/project/pgb-broker-utils


### Work in development ("editable") mode:
```bash
conda env remove --name brokerutils
conda create --name brokerutils python=3.7 pip ipython
conda activate brokerutils
export GOOGLE_APPLICATION_CREDENTIALS=/Users/troyraen/Documents/PGB/repo/GCPauth_pitt-google-broker-prototype-0679b75dded0.json

cd /Users/troyraen/Documents/PGB/repotest/broker/broker_utils
python -m pip install -e .
```
```python
import pgb_utils as pgb

```
