FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       openssh-server \
       openssh-client \
       netcat \
       iperf3 \
       python3 \
       python3-pip \
       python3-venv \
       python3-dev \
       build-essential \
       gcc \
       curl \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/run/sshd

# Create jenkins user for SSH access
RUN useradd -ms /bin/bash jenkins \
    && echo "jenkins:jenkins" | chpasswd

# Install MinIO client (mc)
RUN curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc \
    && chmod +x /usr/local/bin/mc

# Configure SSH
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config \
    && sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config

# Setup SSH key for jenkins user
COPY ssh_keys/jenkins_id_rsa.pub /tmp/jenkins_key.pub
RUN mkdir -p /home/jenkins/.ssh \
    && cp /tmp/jenkins_key.pub /home/jenkins/.ssh/authorized_keys \
    && chown -R jenkins:jenkins /home/jenkins/.ssh \
    && chmod 700 /home/jenkins/.ssh \
    && chmod 600 /home/jenkins/.ssh/authorized_keys

# Copy test_host framework
COPY host_controller/test_host /home/jenkins/test_host

# Install test_host Python dependencies
RUN cd /home/jenkins \
    && python3 -m venv venv \
    && . venv/bin/activate \
    && pip install --no-cache-dir -r test_host/requirements.txt \
    && chown -R jenkins:jenkins /home/jenkins/test_host /home/jenkins/venv

COPY host_controller/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22

CMD ["/entrypoint.sh"]
