# Rescue workflow

In EC2 console → Instance → Actions → Monitor and troubleshoot:
  - Get system log
  - Get instance screenshot

1. Stop the affected instance
2. Detach the root EBS volume
3. Attach to a rescue instance
  - Attach as secondary volume (e.g. `/dev/xvdbf`)
  - Use an instance you can SSH into
4. SSH into the Rescue Instance
```bash
ssh -i ~/.ssh/aws-main-key-2026.pem admin@54.172.16.165
```

5. Mount the volume
```bash
sudo mkdir -p /mnt/rescue
sudo mount /dev/xvdbf1 /mnt/rescue   # partition name may vary
```

## After Fixes

### A. Treat SSH as immutable infrastructure
```bash
sudo systemctl enable ssh
sudo systemctl status ssh
```

Then verify:
```bash
ls -l /etc/systemd/system/multi-user.target.wants/ssh.service
```

### B. Add an explicit boot-time assertion (simple and effective)
Create a drop-in safeguard unit that fails loudly if SSH is not enabled.
```bash
sudo nano /etc/systemd/system/ssh-assert.service
```
```ini
[Unit]
Description=Assert SSH enabled
After=network.target
ConditionPathExists=/etc/systemd/system/multi-user.target.wants/ssh.service

[Service]
Type=oneshot
ExecStart=/bin/true

[Install]
WantedBy=multi-user.target
```
Enable it:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ssh-assert.service
```

### C. Lock down SSH enablement explicitly (optional but strong)
If you want to be aggressive:
```bash
sudo chattr +i /etc/systemd/system/multi-user.target.wants/ssh.service
```
This makes the symlink immutable until you remove the flag.

To undo later:
```bash
sudo chattr -i /etc/systemd/system/multi-user.target.wants/ssh.service
```
This is rarely necessary, but for single-admin servers it is effective.

When you re-enable Docker later, do it intentionally:
```bash
sudo systemctl enable docker
sudo systemctl start docker
```
And ensure:
  - SSH starts before Docker
  - Heavy services (Keycloak) are not auto-started on tiny instances
