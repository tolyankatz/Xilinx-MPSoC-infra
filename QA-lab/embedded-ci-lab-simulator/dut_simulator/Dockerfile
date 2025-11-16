FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       openssh-server \
       socat \
       iperf3 \
       iproute2 \
       iputils-ping \
       net-tools \
    && rm -rf /var/lib/apt/lists/*

# Setup SSH server
RUN mkdir -p /var/run/sshd \
    && mkdir -p /root/.ssh

# Set root password for SSH access
RUN echo 'root:root' | chpasswd

# Configure SSH to allow root login
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22 23

CMD ["/entrypoint.sh"]
