#!/bin/sh
# Substitute $OC_API_KEY in config before starting litellm
python3 -c "
import os
key = os.environ.get('OC_API_KEY', '')
t = open('/app/config.yaml').read()
t = t.replace('\$OC_API_KEY', key)
open('/tmp/config.yaml', 'w').write(t)
print('[entrypoint] config resolved, oc key length:', len(key))
"
exec litellm --config /tmp/config.yaml --port 4000 --num_workers 1
