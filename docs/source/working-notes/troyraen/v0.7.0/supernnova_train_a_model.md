# Train a SuperNNova Model<a name="train-a-supernnova-model"></a>

<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=1 -->

- [Train a SuperNNova Model](#train-a-supernnova-model)
  - [setup](#setup)
  - [train and validate a model using the test set](#train-and-validate-a-model-using-the-test-set)

<!-- mdformat-toc end -->

Links

- [github.com/supernnova/SuperNNova](https://github.com/supernnova/SuperNNova)
- [readthedocs](https://supernnova.readthedocs.io/en/latest/)
- [arXiv paper](https://arxiv.org/pdf/1901.06384.pdf)

Notes

- ssh into `troy`
- create env
- download data
- train models
  - random forest from salt2 fits
  - bayesian RNN

## setup<a name="setup"></a>

folowing the two quickstarts in readthedocs:

```bash
gcloud compute instances start troy
gcloud compute ssh troy

sudo mkdir /home/snn
sudo chown -R troyraen /home/snn
cd /home/snn

# clone the repo to get the env file and test data, and to have a reference
# (will pip install so i can use it as a module)
git clone https://github.com/supernnova/supernnova.git
cd supernnova/env
conda create --name snnenv --file conda_env_cpu_linux64.txt
conda activate snnenv
pip install supernnova

ipython
```

## train and validate a model using the test set<a name="train-and-validate-a-model-using-the-test-set"></a>

```bash
gcloud compute instances start troy
gcloud compute ssh troy
cd /home/snn/supernnova
ipython
```

following the pip quickstart guide in readthedocs:

```python
import supernnova.conf as conf
from supernnova.data import make_dataset
from supernnova.training import train_rnn
from supernnova.validation import validate_rnn


# --- build the database
args = conf.get_args()  # get config args
args.data = True  # making new dataset
args.dump_dir = "tests/dump"  # where the dataset will be saved
args.raw_dir = "tests/raw"  # where raw photometry files are saved
args.fits_dir = "tests/fits"  # conf: where salt2fits are saved
settings = conf.get_settings(args)
make_dataset.make_dataset(settings)
# [troy] this puts the following files in
# tests/dump/figures: multiviolin_test.png
# tests/dump/processed: SNID.pickle, database.h5, hostspe_SNID.pickle

# train RNN
args = conf.get_args()  # [troy] necessary to clear the settings
args.train_rnn = True
args.dump_dir = "tests/dump"  # where the dataset is saved
args.nb_epoch = 2  # training epochs
settings = conf.get_settings(args)  # set settings
train_rnn.train(settings)  # train rnn
# [troy] creates the following dir with some .json, .png, and .pt files in it
# dump/models/vanilla_S_0_CLF_2_R_none_photometry_DF_1.0_N_global_lstm_32x2_0.05_128_True_mean

# validate RNN
args = conf.get_args()
args.validate_rnn = False  # validate rnn
args.dump_dir = "tests/dump"  # where the dataset is saved
settings = conf.get_settings(args)
validate_rnn.get_predictions(settings)  # classify test set
# [troy] adds the following file to dump/models/vanilla_S_0_CLF_2_R_none_photometry_DF_1.0_N_global_lstm_32x2_0.05_128_True_mean:
# PRED_vanilla_S_0_CLF_2_R_none_photometry_DF_1.0_N_global_lstm_32x2_0.05_128_True_mean.pickle
```
