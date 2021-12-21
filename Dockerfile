FROM python:3.9

# Set the working directory to /app
WORKDIR /app

#RUN apk update && apk install gcc

# Copy the current directory contents into the container at /app
ADD . /app

# Install the dependencies
RUN pip install -r requirements.txt

# Create a uwsgi log directory and files
RUN mkdir /var/log/uwsgi
RUN touch /var/log/uwsgi/uwsgi_access.log
RUN touch /var/log/uwsgi/uwsgi_error.log

# run the command to start uWSGI
CMD ["uwsgi", "app.ini"]
