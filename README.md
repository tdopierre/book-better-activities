# Book Better Activities

An automated activity booking system for Better UK leisure facilities. This tool logs into your Better leisure account, searches for available activity slots, and automatically books them on a schedule.

## Features

- YAML-based configuration for multiple booking jobs
- Built-in scheduler with cron expressions (no system cron required)
- Environment variable substitution in config
- YAML anchors for reusable credentials
- Automatic retry mechanism for reliable API interactions
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

3. Set environment variables for your Better account:
   ```bash
   export BETTER_USERNAME=your_username
   export BETTER_PASSWORD=your_password
   ```

4. Configure your bookings in `config.yaml`

## Configuration

Edit `config.yaml` to define your booking jobs:

```yaml
# Shared credentials using YAML anchors
credentials: &credentials
  username: <BETTER_USERNAME>  # Reads from environment
  password: <BETTER_PASSWORD>  # Reads from environment

bookings:
  - name: "Weekday evening badminton"
    <<: *credentials           # Merge shared credentials
    venue: queensbridge-sports-community-centre
    activity: badminton-40min
    min_slot_time: "18:00:00"
    n_slots: 2
    days_ahead: 4
    schedule: "0 22 * * 1-5"   # Cron: 10 PM, Mon-Fri

  - name: "Weekend badminton"
    <<: *credentials
    venue: britannia-leisure-centre
    activity: badminton-40min
    min_slot_time: "10:00:00"
    n_slots: 2
    days_ahead: 4
    schedule: "0 9 * * 6"      # Cron: 9 AM, Saturday
```

### Configuration Options

| Option | Description | Example |
|--------|-------------|---------|
| `name` | Unique name for the booking job | `"Weekday badminton"` |
| `username` | Better account username (or `<ENV_VAR>`) | `<BETTER_USERNAME>` |
| `password` | Better account password (or `<ENV_VAR>`) | `<BETTER_PASSWORD>` |
| `venue` | Venue slug | `queensbridge-sports-community-centre` |
| `activity` | Activity slug | `badminton-40min` |
| `min_slot_time` | Minimum time filter (HH:MM:SS) | `"18:00:00"` |
| `n_slots` | Number of consecutive slots to book | `2` |
| `days_ahead` | Days in advance to book | `4` |
| `schedule` | Cron expression for scheduling | `"0 22 * * 1-5"` |

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

## Usage

### Run Locally

```bash
uv run python src/scripts/book-activity.py
```

The scheduler will start and execute booking jobs according to their cron schedules.

### Docker Deployment

```bash
# Build the image
docker build -t book-better-activities .

# Run with environment variables
docker run -d \
  -e BETTER_USERNAME=your_username \
  -e BETTER_PASSWORD=your_password \
  --name better-booker \
  book-better-activities
```

Or mount a custom config:
```bash
docker run -d \
  -e BETTER_USERNAME=your_username \
  -e BETTER_PASSWORD=your_password \
  -v /path/to/config.yaml:/app/config.yaml \
  --name better-booker \
  book-better-activities
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

## How It Works

1. **Config Loading**: Reads `config.yaml`, substitutes environment variables, and validates with Pydantic
2. **Scheduling**: APScheduler sets up cron triggers for each booking job
3. **Authentication**: Logs into the Better API with credentials and obtains a JWT token
4. **Search**: Fetches available activity times for the target date (N days in advance)
5. **Filter**: Filters slots by time and availability
6. **Book**: Adds selected slots to cart and completes checkout using account credits

## Development

### Code Quality

```bash
# Format with black
black .

# Lint with ruff
ruff check .
```

## License

Private project - not for redistribution.
