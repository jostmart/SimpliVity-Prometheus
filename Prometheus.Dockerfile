# docker build -t prometheus:tb -f Prometheus.Dockerfile .
# Use prom/prometheus as the base Image
FROM  prom/prometheus
LABEL maintainer="Thomas Beha"
LABEL version="1.0"
LABEL copyright="Thomas Beha, 2019"
LABEL license="GNU General Public License v3"
LABEL DESCRIPTION="Prometheus Connector"
# Copy the scrape instruction   
COPY prometheus.yml /etc/prometheus/