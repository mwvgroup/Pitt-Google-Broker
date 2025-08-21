# docs/source/working-notes/troyraen/v0.6.0/test-stream-looper.md

## Test pricing and functionality of stream-looper long term

Started stream-looper around 11:00 am ET on Aug 7, publishing 1 alert/sec.

It ran for about 20 hours, which is 2 "night"s, or two iterations of the while loop. Then it quit with this error:

```
Traceback (most recent call last):
  File "/usr/local/lib/python3.7/dist-packages/google/api_core/grpc_helpers.py", line 67, in error_remapped_callable
    return callable_(*args, **kwargs)
```

Rebooted stream-looper around 10:15 pm ET on Aug 8.
