# Book Better Activities

An automated activity booking system for Better UK leisure facilities. This tool logs into your Better leisure account, searches for available activity slots, and automatically books them.

## Features

- Automated booking of badminton sessions (40-minute slots)
- Configurable venue, activity type, and time filters
- Book multiple consecutive slots in one operation
- Automatic retry mechanism for reliable API interactions
- Scheduled execution via cron for hands-free booking
- Docker containerization for easy deployment

## Requirements

- Python 3.12+
- A Better UK leisure account with credits

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd book-better-activities
   ```

2. Install dependencies using [uv](https://github.com/astral-sh/uv):
   ```bash
   uv sync
   ```

3. Create a `.env` file with your Better account credentials:
   ```bash
   BETTER_USERNAME=your_username
   BETTER_PASSWORD=your_password
   ```

## Usage

### Command Line

Run the booking script with the desired parameters:

```bash
typer src/scripts/book-activity.py run \
  --venue queensbridge-sports-community-centre \
  --activity badminton-40min \
  --min-slot-time 18:00:00 \
  --n-slots 2
```

### Options

| Option | Description | Example |
|--------|-------------|---------|
| `--venue` | Target leisure venue | `queensbridge-sports-community-centre` |
| `--activity` | Activity type to book | `badminton-40min` |
| `--min-slot-time` | Minimum time filter (HH:MM:SS) | `18:00:00` |
| `--n-slots` | Number of consecutive slots to book | `2` |

### Supported Venues

- `queensbridge-sports-community-centre`
- `britannia-leisure-centre`

### Supported Activities

- `badminton-40min`

## Docker Deployment

Build and run with Docker for scheduled automated booking:

```bash
# Build the image
docker build -t book-better-activities .

# Run the container
docker run -d --name better-booker book-better-activities
```

The container runs a cron job that executes bookings every weekday at 22:00 (10 PM).

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BETTER_USERNAME` | Your Better account username | Yes |
| `BETTER_PASSWORD` | Your Better account password | Yes |

### Cron Schedule

The default cron schedule (in `test.crontab`) runs:
- Every weekday (Monday-Friday) at 22:00
- Books 2 consecutive badminton slots at Queensbridge
- Filters for slots starting at 18:00 or later

Modify `test.crontab` to customize the schedule.

## Project Structure

```
book-better-activities/
├── src/
│   ├── clients/
│   │   └── better_client.py    # API client for Better.org.uk
│   ├── scripts/
│   │   └── book-activity.py    # CLI entry point
│   ├── config.py               # Settings management
│   ├── exceptions.py           # Custom exceptions
│   ├── logging.py              # Logging utilities
│   └── models.py               # Data models (Pydantic)
├── main.py                     # Root entry point
├── pyproject.toml              # Project dependencies
├── Dockerfile                  # Container configuration
├── test.crontab                # Cron job schedule
└── uv.lock                     # Dependency lock file
```

## How It Works

1. **Authentication**: Logs into the Better API with your credentials and obtains a JWT token
2. **Search**: Fetches available activity times for the target date (4 days in advance)
3. **Filter**: Filters slots by time, availability, and existing bookings
4. **Book**: Adds selected slots to cart and completes checkout using account credits

## Development

### Code Quality

Format and lint the code:

```bash
# Format with black
black .

# Lint with ruff
ruff check .
```

## License

Private project - not for redistribution.
