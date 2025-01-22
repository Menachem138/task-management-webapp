FROM python:3.12-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY telegram_bot.py ./

# Configure poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Create logs directory
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Run the bot
CMD ["poetry", "run", "python", "telegram_bot.py"]
