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
ssh -i ~/.ssh/aws-main-key.pem admin@54.172.16.165
```
, or maybe `aws-main-key-2026`

5. Mount the volume
```bash
sudo mkdir -p /mnt/rescue
sudo mount /dev/xvdf1 /mnt/rescue   # partition name may vary
```
