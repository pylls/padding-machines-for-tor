FROM ubuntu:rolling
MAINTAINER Tobias Pulls <tobias.pulls@kau.se>

# install and clean since we'll be running many copies
RUN apt-get update && apt-get install -y \
        dumb-init \
        python3 \
        python3-requests \
        firefox
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# setup a user to not run as root
ENV HOME /home/user
ENV LANG C.UTF-8
RUN useradd --create-home --home-dir $HOME user
WORKDIR $HOME
USER user

ENTRYPOINT ["dumb-init", "--"]
