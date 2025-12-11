# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set the working directory to /app
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy the lockfile and pyproject.toml
COPY uv.lock pyproject.toml /app/

# Install the project's dependencies using the lockfile and settings
RUN uv sync --frozen --no-install-project

# Copy the rest of the project source code
COPY . /app

# Place the executables in the environment at the front of the path
# This allows us to run `python` and `uv` commands directly
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Run the application
CMD ["uv", "run", "main.py"]
