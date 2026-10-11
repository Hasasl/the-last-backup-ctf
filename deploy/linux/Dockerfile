FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends openssh-server coreutils less && rm -rf /var/lib/apt/lists/* \
 && groupadd -g 2000 evidence && useradd -m -u 2000 -g evidence -s /bin/bash -p '*' analyst \
 && mkdir -p /srv/northstar /home/analyst/work /etc/ssh/authorized_keys /run/sshd \
 && chown root:root /home/analyst && chmod 755 /home/analyst
COPY sshd_config /etc/ssh/sshd_config
COPY entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh
EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
