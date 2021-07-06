#Grab python=3.9-slim-buster image
FROM python:3.9-slim-buster


# Copy code to container
COPY . .

# RUN apt-get update
RUN apt-get update && apt-get install -y build-essential wget python3-dev python3-pip gcc
# openldap-dev libffi-dev jpeg-dev zlib-dev libmemcached-dev gcc libc-dev g++ libxml2 libxslt libxslt-dev

# TA-Lib
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
  tar -xvzf ta-lib-0.4.0-src.tar.gz && \
  cd ta-lib/ && \
  ./configure --prefix=/usr && \
  make && \
  make install && \
  cd ..
RUN rm -R ta-lib ta-lib-0.4.0-src.tar.gz

# Move working directory
WORKDIR /app

# Install python depencies
RUN pip3 install --upgrade pip && pip3 install --no-cache-dir -q -r requirements.txt

# Expose is NOT supported by Heroku
# EXPOSE 5000 		

# Run the image as a non-root user
RUN adduser myuser
USER myuser

# Run the app.  CMD is required to run on Heroku
# $PORT is set by Heroku			
CMD gunicorn --bind 0.0.0.0:$PORT --timeout 600 app:app 
# CMD gunicorn --bind 0.0.0.0:5000 app:app 