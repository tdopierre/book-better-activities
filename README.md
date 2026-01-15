# Book Better Activities

[![Build](https://github.com/tdopierre/book-better-activities/actions/workflows/docker.yml/badge.svg)](https://github.com/tdopierre/book-better-activities/actions/workflows/docker.yml)

An automated activity booking system for Better UK leisure facilities. This tool logs into your Better leisure account, searches for available activity slots, and automatically books them on a schedule with smart fallback options.

## Features

- **Multiple Fallback Attempts**: Configure multiple booking preferences per job - the system tries each in order until one succeeds
- **Discord Notifications**: Get notified on Discord when bookings succeed or fail
- **YAML-based Configuration**: Define multiple booking jobs with flexible options
- **Built-in Scheduler**: Uses APScheduler with cron expressions (no system cron required)
- **Environment Variable Substitution**: Securely reference credentials and webhook URLs
- **YAML Anchors**: Reuse credentials across multiple booking jobs
- **Automatic Retry**: Reliable API interactions with exponential backoff

## Quick Start

### Scheduled Booking (runs continuously)

1. Create a `config.yaml` file (see [Configuration](#configuration))

2. Run with Docker:
   ```bash
   docker run -d \
     -e BETTER_USERNAME=your_username \
     -e BETTER_PASSWORD=your_password \
     -e DISCORD_WEBHOOK_URL=your_webhook_url \
     -v /path/to/config.yaml:/app/config.yaml \
     --name better-booker \
     ghcr.io/tdopierre/book-better-activities:latest
   ```

### One-Shot Booking (runs once and exits)

Book immediately without a config file:

```bash
docker run --rm --env-file .env \
  ghcr.io/tdopierre/book-better-activities:latest \
  uv run python src/scripts/book_now.py \
    --venue queensbridge-sports-community-centre \
    --activity badminton-40min \
    --date 2026-01-19 \
    --min-slot-time 16:40:00 \
    --max-slot-time 19:20:00 \
    --n-slots 2
```

## Configuration

Create a `config.yaml` file to define your booking jobs with fallback attempts:

```yaml
# Book Better Activities Configuration
# Environment variables can be referenced using <ENV_VAR> syntax
#
# Discord Notifications:
# To get a webhook URL: Server Settings > Integrations > Webhooks > New Webhook
# Then set the DISCORD_WEBHOOK_URL environment variable or paste the URL directly

# Shared credentials (use YAML anchors for reuse)
credentials: &credentials
  username: <BETTER_USERNAME>
  password: <BETTER_PASSWORD>

bookings:
  # Weekday evening badminton with fallback options
  - name: "Weekday evening badminton"
    days_ahead: 7
    schedule: "0 22 * * 1-5"  # 10 PM, Monday-Friday
    discord_webhook_url: <DISCORD_WEBHOOK_URL>  # Optional: Discord webhook for notifications
    attempts:
      # First choice: Queensbridge, 2 slots, 6-9 PM
      - <<: *credentials
        venue: queensbridge-sports-community-centre
        activity: badminton-40min
        min_slot_time: "18:00:00"
        max_slot_time: "21:00:00"
        n_slots: 2

      # Fallback 1: Same venue/activity, accept 1 slot if 2 not available
      - <<: *credentials
        venue: queensbridge-sports-community-centre
        activity: badminton-40min
        min_slot_time: "18:00:00"
        max_slot_time: "21:00:00"
        n_slots: 1

      # Fallback 2: Try earlier time window (5-9 PM), 2 slots
      - <<: *credentials
        venue: queensbridge-sports-community-centre
        activity: badminton-40min
        min_slot_time: "17:00:00"
        max_slot_time: "21:00:00"
        n_slots: 2

      # Fallback 3: Different venue (Britannia)
      - <<: *credentials
        venue: britannia-leisure-centre
        activity: badminton-40min
        min_slot_time: "18:00:00"
        max_slot_time: "21:00:00"
        n_slots: 2

  # Example: Single-attempt booking (simplest case)
  # - name: "Weekend badminton"
  #   days_ahead: 4
  #   schedule: "0 9 * * 6"  # 9 AM, Saturday
  #   discord_webhook_url: <DISCORD_WEBHOOK_URL>
  #   attempts:
  #     - <<: *credentials
  #       venue: britannia-leisure-centre
  #       activity: badminton-40min
  #       min_slot_time: "10:00:00"
  #       max_slot_time: "12:00:00"
  #       n_slots: 2
```

### Configuration Options

#### Booking Job Level

| Option | Description | Example | Required |
|--------|-------------|---------|----------|
| `name` | Unique name for the booking job | `"Weekday badminton"` | Yes |
| `schedule` | Cron expression for when to run | `"0 22 * * 1-5"` | Yes |
| `days_ahead` | How many days in advance to book | `7` | Yes |
| `attempts` | List of booking attempts (tries in order) | See below | Yes |
| `discord_webhook_url` | Discord webhook URL for notifications | `<DISCORD_WEBHOOK_URL>` | No |

#### Booking Attempt Level

Each attempt in the `attempts` list supports:

| Option | Description | Example | Required |
|--------|-------------|---------|----------|
| `username` | Better account username | `<BETTER_USERNAME>` | Yes |
| `password` | Better account password | `<BETTER_PASSWORD>` | Yes |
| `venue` | Venue slug | `queensbridge-sports-community-centre` | Yes |
| `activity` | Activity slug | `badminton-40min` | Yes |
| `min_slot_time` | Only book slots starting at this time or later | `"18:00:00"` | Yes |
| `max_slot_time` | Only book slots ending by this time | `"21:00:00"` | No |
| `n_slots` | Number of consecutive slots to book | `2` | No (default: 1) |

### Environment Variable Substitution

Use `<ENV_VAR>` syntax to reference environment variables:
```yaml
username: <BETTER_USERNAME>         # Replaced with $BETTER_USERNAME value
password: <BETTER_PASSWORD>         # Replaced with $BETTER_PASSWORD value
discord_webhook_url: <DISCORD_WEBHOOK_URL>  # Replaced with $DISCORD_WEBHOOK_URL value
```

### Discord Notifications

To enable Discord notifications:

1. **Create a webhook in Discord:**
   - Go to your server → Server Settings → Integrations → Webhooks
   - Click "New Webhook"
   - Copy the webhook URL

2. **Configure the webhook:**
   - Set environment variable: `export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."`
   - Or paste directly in `config.yaml`

3. **Notifications sent:**
   - ✅ **Success notification** (green) when a booking succeeds - shows attempt number and order ID
   - ❌ **Failure notification** (red) when all attempts fail - shows all error details

Notifications are **optional** - the system works without them if no webhook URL is provided.

## How It Works

### Fallback Logic

Each booking job tries its attempts in order until one succeeds:

1. **Attempt 1**: Try your preferred configuration (e.g., 2 slots at venue A, 6-9 PM)
2. **Attempt 2**: If that fails, try fallback (e.g., 1 slot at same venue/time)
3. **Attempt 3**: If that fails, try another fallback (e.g., different time window)
4. **Attempt 4**: If that fails, try final fallback (e.g., different venue)

**Stops at first success** - Once an attempt succeeds, remaining attempts are skipped.

**Only fails if all attempts fail** - You get a notification with all error details.

### Booking Process

For each attempt:

1. **Parse Time Window**: Convert time strings to time objects
2. **Authentication**: Log into Better API and obtain JWT token
3. **Fetch Available Times**: Get all available slots for the activity/date
4. **Filter by Time Window**: Keep only slots within min/max time range
5. **Find Consecutive Slots**: Look for N consecutive slots (where each slot's end = next slot's start)
6. **Convert to Bookable Slots**: Get specific slot IDs from API
7. **Complete Booking**: Add to cart and checkout using account credits
8. **Notify**: Send Discord notification on success

If an attempt fails at any step, move to next attempt. If all attempts fail, send failure notification.

### Scheduler

- **Config Loading**: Reads `config.yaml`, substitutes environment variables, validates with Pydantic
- **Credential Validation**: Validates all unique credential pairs at startup
- **Cron Scheduling**: APScheduler sets up cron triggers for each booking job
- **Execution**: Jobs run at scheduled times, trying all attempts with fallback logic

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
export DISCORD_WEBHOOK_URL=your_webhook_url  # Optional
uv run python src/scripts/scheduled_booking.py
```

### Build Docker Image

```bash
docker build -t book-better-activities .
```

### Code Quality

```bash
make format     # Auto-fix formatting
make fix-lint   # Fix linting issues
make lint       # Check formatting and linting
```

## Project Structure

```
book-better-activities/
├── Dockerfile                   # Container configuration
├── Makefile                     # Build/lint commands
├── config.yaml                  # Booking configuration
├── pyproject.toml               # Project dependencies
├── uv.lock                      # Dependency lock file
└── src/
    ├── booking.py               # Core booking logic with fallback
    ├── clients/
    │   └── better_client.py     # API client for Better.org.uk
    ├── config.py                # YAML config loader with validation
    ├── exceptions.py            # Custom exceptions
    ├── logging.py               # Logging utilities
    ├── models.py                # Data models (Pydantic)
    ├── notifications.py         # Discord notification functions
    ├── scripts/
    │   ├── book_now.py          # One-shot booking script
    │   ├── list_slots.py        # List available slots script
    │   └── scheduled_booking.py # Main scheduler entry point
    └── __init__.py              # Python package initializer
```

## Common Use Cases

### Maximize Booking Success

Configure multiple fallback attempts with decreasing requirements:
1. **Ideal**: 2 consecutive slots, peak time, preferred venue
2. **Good**: 1 slot (better than nothing), same time/venue
3. **Acceptable**: 2 slots, wider time window
4. **Last Resort**: Different venue

### Different Credentials Per Venue

Each attempt can use different credentials:
```yaml
attempts:
  - username: <USER1>
    password: <PASS1>
    venue: venue-a
    # ...
  - username: <USER2>
    password: <PASS2>
    venue: venue-b
    # ...
```

### Vary Time Windows

Try progressively wider time windows:
```yaml
attempts:
  - min_slot_time: "18:00:00"
    max_slot_time: "20:00:00"  # Narrow window
    # ...
  - min_slot_time: "17:00:00"
    max_slot_time: "21:00:00"  # Wider window
    # ...
```

## Supported Venues

- `queensbridge-sports-community-centre`
- `britannia-leisure-centre`
- (Add more as discovered)

## Supported Activities

- `badminton-40min`
- (Add more as discovered)

## License

Private project - not for redistribution.
