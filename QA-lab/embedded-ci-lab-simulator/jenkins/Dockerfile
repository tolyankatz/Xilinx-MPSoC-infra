FROM jenkins/jenkins:lts-jdk11

USER root

RUN apt-get update \
    && apt-get install -y docker.io \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -f docker \
    && usermod -aG docker jenkins

COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
COPY casc.yaml /usr/share/jenkins/ref/casc.yaml

RUN jenkins-plugin-cli -f /usr/share/jenkins/ref/plugins.txt

# Create directories for init scripts and the seed job
RUN mkdir -p /usr/share/jenkins/ref/init.groovy.d \
    && mkdir -p /usr/share/jenkins/ref/jobs/seed-job \
    && mkdir -p /usr/share/jenkins/ref/dsl

# Copy the security init script
COPY security.groovy /usr/share/jenkins/ref/init.groovy.d/security.groovy

# Copy the seed job configuration and the DSL script to create the pipeline
# (Assumes you have seed_job_config.xml and seed.groovy from the previous answer)
COPY seed_job_config.xml /usr/share/jenkins/ref/jobs/seed-job/config.xml
COPY seed.groovy /usr/share/jenkins/ref/dsl/seed.groovy

USER jenkins