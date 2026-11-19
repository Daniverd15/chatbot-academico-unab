#!/bin/bash
# Aprovisiona la infraestructura en AWS (ejecutar en AWS CloudShell, us-east-1)
set -e
# Llave SSH: si exportas PUBKEY="ssh-rsa AAAA..." se importa tu llave pública;
# si no, se crea un key pair nuevo y la llave privada queda en ~/chatbot-unab-key.pem (descárgala de CloudShell).
if [ -n "${PUBKEY:-}" ]; then
  echo "$PUBKEY" > /tmp/k.pub
  aws ec2 import-key-pair --key-name chatbot-unab-key --public-key-material fileb:///tmp/k.pub 2>/dev/null || echo "llave ya existe"
elif ! aws ec2 describe-key-pairs --key-names chatbot-unab-key >/dev/null 2>&1; then
  aws ec2 create-key-pair --key-name chatbot-unab-key --query KeyMaterial --output text > ~/chatbot-unab-key.pem && chmod 400 ~/chatbot-unab-key.pem
  echo "Llave privada guardada en ~/chatbot-unab-key.pem"
fi
VPC=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
SG=$(aws ec2 create-security-group --group-name chatbot-unab-sg --description "Chatbot UNAB n8n+MCP" --vpc-id $VPC --query GroupId --output text 2>/dev/null || aws ec2 describe-security-groups --group-names chatbot-unab-sg --query 'SecurityGroups[0].GroupId' --output text)
for P in 22 80 443 5678 9000; do aws ec2 authorize-security-group-ingress --group-id $SG --protocol tcp --port $P --cidr 0.0.0.0/0 2>/dev/null || true; done
AMI=$(aws ec2 describe-images --owners 099720109477 --filters "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*" --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text)
cat > /tmp/ud.sh <<'UD'
#!/bin/bash
fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab
apt-get update -y && apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu
timedatectl set-timezone America/Bogota
UD
ID=$(aws ec2 run-instances --image-id $AMI --instance-type t3.medium --key-name chatbot-unab-key --security-group-ids $SG --user-data file:///tmp/ud.sh --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=30,VolumeType=gp3}' --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=chatbot-unab}]' --query 'Instances[0].InstanceId' --output text)
aws ec2 wait instance-running --instance-ids $ID
EIP=$(aws ec2 allocate-address --query AllocationId --output text) && aws ec2 associate-address --instance-id $ID --allocation-id $EIP >/dev/null || true
echo "INSTANCIA=$ID"; aws ec2 describe-instances --instance-ids $ID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text
