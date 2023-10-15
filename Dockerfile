# Use the official Python image as a parent image
FROM python:3.10

ENV PYTHONUNBUFFERED True
RUN apt-get update \
    && apt-get -y install libpq-dev gcc 

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install any dependencies
RUN pip install -r requirements.txt

COPY . /app/

# Expose the port your FASTAPI app is running on
EXPOSE 8080

# Start the FASTAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]