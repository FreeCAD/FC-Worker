# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com>
# SPDX-FileCopyrightText: 2026 Amritpal Singh <amrit3701@gmail.com>


FROM amrit3701/freecad-cli:1.0.2-amd64-ubuntu22.04-py3.11-qt5

WORKDIR /

ENV LANG=en_US.UTF-8
RUN apt-get update && apt-get install -y locales && \
    sed -i -e "s/# $LANG.*/$LANG UTF-8/" /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=$LANG
ENV LC_ALL=en_US.UTF-8
ENV LANGUAGE=en_US:en

COPY requirements/aws.txt  requirements.txt
RUN  pip3 install -r requirements.txt

COPY fc_worker/ /fc_worker/.

ADD https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie /usr/bin/aws-lambda-rie

COPY entry.sh lambda.py /

RUN chmod 755 /usr/bin/aws-lambda-rie /entry.sh

ENTRYPOINT [ "/entry.sh" ]

CMD [ "lambda.lambda_handler" ]
