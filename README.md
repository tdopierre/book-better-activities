# Book Better Activities

[![Build](https://github.com/tdopierre/book-better-activities/actions/workflows/docker.yml/badge.svg)](https://github.com/tdopierre/book-better-activities/actions/workflows/docker.yml)

An automated activity booking system for Better UK leisure facilities. This tool logs into your Better leisure account, searches for available activity slots, and automatically books them on a schedule.

## Features

- YAML-based configuration for multiple booking jobs
- Built-in scheduler with cron expressions (no system cron required)
- Environment variable substitution in config
- YAML anchors for reusable credentials
- Automatic retry mechanism for reliable API interactions

## Quick Start

1. Create a `config.yaml` file (see [Configuration](#configuration))

2. Run with Docker:
   ```bash
   docker run -d \
     -e BETTER_USERNAME=your_username \
     -e BETTER_PASSWORD=your_password \
     -v /path/to/config.yaml:/app/config.yaml \
     --name better-booker \
     ghcr.io/tdopierre/book-better-activities:latest
   ```

## Configuration

Create a `config.yaml` file to define your booking jobs:

```yaml
# Shared credentials using YAML anchors
credentials: &credentials
  username: <BETTER_USERNAME>  # Reads from environment
  password: <BETTER_PASSWORD>  # Reads from environment

# Note: Better venues typically open bookings at 22:00 (10 PM)
bookings:
  - name: "Weekday evening badminton"
    <<: *credentials           # Merge shared credentials
    venue: queensbridge-sports-community-centre
    activity: badminton-40min
    min_slot_time: "18:00:00"  # Book slots starting at 6 PM or later
    max_slot_time: "21:00:00"  # Book slots ending by 9 PM
    n_slots: 2                 # Book 2 consecutive 40-min slots (1h20 total)
    days_ahead: 7              # Book 1 week in advance
    schedule: "0 22 * * 1-5"   # Cron: 10 PM, Mon-Fri

  - name: "Weekend badminton"
    <<: *credentials
    venue: britannia-leisure-centre
    activity: badminton-40min
    min_slot_time: "10:00:00"  # Book slots starting at 10 AM or later
    max_slot_time: "14:00:00"  # Book slots ending by 2 PM
    n_slots: 2                 # Book 2 consecutive 40-min slots (1h20 total)
    days_ahead: 7              # Book 1 week in advance
    schedule: "0 22 * * 5"     # Cron: 10 PM, Friday (for Saturday booking)
```

### Options

| Option | Description | Example |
|--------|-------------|---------|
| `name` | Unique name for the booking job | `"Weekday badminton"` |
| `username` | Better account username (or `<ENV_VAR>`) | `<BETTER_USERNAME>` |
| `password` | Better account password (or `<ENV_VAR>`) | `<BETTER_PASSWORD>` |
| `venue` | Venue slug | `queensbridge-sports-community-centre` |
| `activity` | Activity slug | `badminton-40min` |
| `min_slot_time` | Only book slots starting at this time or later | `"18:00:00"` |
| `max_slot_time` | Only book slots ending by this time (optional) | `"21:00:00"` |
| `n_slots` | Number of consecutive slots to book | `2` |
| `days_ahead` | How many days in advance to book (e.g., 7 = 1 week) | `7` |
| `schedule` | Cron expression for when to run the booking | `"0 22 * * 1-5"` |

### Environment Variable Substitution

Use `<ENV_VAR>` syntax to reference environment variables:
```yaml
username: <BETTER_USERNAME>   # Replaced with $BETTER_USERNAME value
password: <BETTER_PASSWORD>   # Replaced with $BETTER_PASSWORD value
```

### Supported Venues

- `queensbridge-sports-community-centre`
- `britannia-leisure-centre`

### Supported Activities

- `badminton-40min`

## How It Works

1. **Config Loading**: Reads `config.yaml`, substitutes environment variables, and validates with Pydantic
2. **Scheduling**: APScheduler sets up cron triggers for each booking job
3. **Authentication**: Logs into the Better API with credentials and obtains a JWT token
4. **Search**: Fetches available activity times for the target date (N days in advance)
5. **Filter**: Filters slots by time and availability
6. **Book**: Adds selected slots to cart and completes checkout using account credits

## Development

### Local Setup

```bash
git clone https://github.com/tdopierre/book-better-activities.git
cd book-better-activities
uv sync
```

### Run Locally

```bash
export BETTER_USERNAME=your_username
export BETTER_PASSWORD=your_password
uv run python src/scripts/book-activity.py
```

### Build Docker Image

```bash
docker build -t book-better-activities .
```

### Code Quality

```bash
make lint    # Check formatting
make format  # Auto-fix formatting
```

## Project Structure

```
book-better-activities/
├── src/
│   ├── clients/
│   │   └── better_client.py    # API client for Better.org.uk
│   ├── scripts/
│   │   └── book-activity.py    # Main scheduler entry point
│   ├── config.py               # YAML config loader
│   ├── exceptions.py           # Custom exceptions
│   ├── logging.py              # Logging utilities
│   └── models.py               # Data models (Pydantic)
├── config.yaml                 # Booking configuration
├── pyproject.toml              # Project dependencies
├── Dockerfile                  # Container configuration
└── uv.lock                     # Dependency lock file
```

## License

Private project - not for redistribution.
