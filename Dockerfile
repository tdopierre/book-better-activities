FROM python:3.12-slim

# Update
RUN apt-get update
RUN apt-get -y install cron
RUN python3 -m pip install uv

# Set up working dir
WORKDIR /app
COPY . /app

# Install reqs
RUN uv sync
# RUN source .venv/bin/activate
ENV PYTHONPATH="$PYTHONPATH:/app"

# CRON
COPY test.crontab /etc/cron.d/crontab
RUN chmod 0644 /etc/cron.d/crontab
RUN /usr/bin/crontab /etc/cron.d/crontab

# CMD [".venv/bin/python", "src/clients/better_client.py"]
# run crond as main process of container
CMD ["cron", "-f"]