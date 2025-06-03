# Use an official Python runtime as a parent image
FROM python:3.13.1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run post-installation setup
RUN playwright install --with-deps

# Copy the current directory contents into the container at /app
COPY . .

# Expose the port the app runs on
EXPOSE 8000 

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["python", "run.py"]