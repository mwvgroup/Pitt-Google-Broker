# PyPI setup
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

## Build the distribution and upload it
```bash
cd /Users/troyraen/Documents/PGB/repo/pgb_utils
python3 -m build
python3 -m twine upload --repository testpypi dist/*
```
View at: https://test.pypi.org/project/pgb-utils-alpha/0.0.1/


## Work in development ("editable") mode:
```bash
cd /Users/troyraen/Documents/PGB/repo/pgb_utils
python -m pip install -e .
```
```python
import pgb_utils_alpha as pgb

```
