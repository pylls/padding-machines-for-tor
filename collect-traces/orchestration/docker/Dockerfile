FROM ubuntu:rolling
MAINTAINER Tobias Pulls <tobias.pulls@kau.se>

# install and clean since we'll be running many copies
RUN apt-get update && apt-get install -y \
        dumb-init \
        python3 \
        tshark \
        firefox
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# setup a user to not run as root
ENV HOME /home/user
ENV LANG C.UTF-8
RUN useradd --create-home --home-dir $HOME user

# capabilities to run tshark, note that you also need to later: 
# docker run --cap-add=NET_RAW --cap-add=NET_ADMIN
RUN groupadd wireshark && \
    usermod -aG wireshark user && \
    chgrp wireshark /usr/bin/dumpcap && \
    chmod 750 /usr/bin/dumpcap && \
    setcap 'CAP_NET_RAW+eip CAP_NET_ADMIN+eip' /usr/bin/dumpcap

WORKDIR $HOME
USER user

ENTRYPOINT ["dumb-init", "--"]
