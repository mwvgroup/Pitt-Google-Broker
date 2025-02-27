# SuperNNova Classifier

This Cloud Run instance classifies alerts using
[SuperNNova](https://supernnova.readthedocs.io/en/latest/index.html).

The code follows SuperNNova's
[run_onthefly.py](https://github.com/supernnova/SuperNNova/blob/master/run_onthefly.py)
example.

The trained model (and related configs/info) is packaged with the Cloud Function.
The directory name represents the training dataset
(todo: add information about the training data).
The trained model's filename follows these
[naming conventions](https://supernnova.readthedocs.io/en/latest/installation/five_minute_guide.html#naming-conventions).
