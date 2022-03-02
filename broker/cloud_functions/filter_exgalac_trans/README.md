# Extragalactic Transients Filter

This Cloud Function filters the alert stream for likely extragalactic transients. It
emits the Pub/Sub stream "exgalac_trans_cf". The "\_cf" differentiates this stream from
the one emitted by the Dataflow job, which contains the same filter. It is implemented
in both places for comparison of the methods.
