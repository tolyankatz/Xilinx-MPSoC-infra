FROM jenkins/jenkins:lts-jdk11

USER root

RUN apt-get update \
    && apt-get install -y openssh-client curl \
    && rm -rf /var/lib/apt/lists/*

# Install MinIO client
RUN curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc \
    && chmod +x /usr/local/bin/mc

# Install suggested plugins
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli -f /usr/share/jenkins/ref/plugins.txt

# Create SSH directory
RUN mkdir -p /var/jenkins_home/.ssh \
    && chown -R jenkins:jenkins /var/jenkins_home/.ssh \
    && chmod 700 /var/jenkins_home/.ssh

USER jenkins
