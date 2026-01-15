import asyncio
import datetime
import json
import logging
from zoneinfo import ZoneInfo

import discord
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from discord import app_commands
from dotenv import load_dotenv

from src.clients.better_client import get_client
from src.config import (
    AppConfig,
    load_config,
)
from src.scripts.scheduled_booking import (
    parse_cron_expression,
    run_scheduled_booking,
    validate_credentials,
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Load application configuration
config: AppConfig = load_config()

# Initialize scheduler
scheduler = AsyncIOScheduler()

# Setup Discord bot
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@tree.command(name="list-bookings", description="List your upcoming bookings")
async def list_bookings(interaction: discord.Interaction):
    """Slash command to list upcoming bookings."""
    await interaction.response.defer(ephemeral=True)
    try:
        logger.info("Listing bookings via Discord command")
        # For simplicity, this uses the first credential in the first booking config
        # This could be improved to select credentials or handle multiple users
        if not config.bookings:
            await interaction.followup.send("No booking configurations found.")
            return

        first_booking_attempt = config.bookings[0].attempts[0]
        better_client = get_client(
            username=first_booking_attempt.username,
            password=first_booking_attempt.password,
        )
        bookings = better_client.get_my_bookings()

        if not bookings:
            await interaction.followup.send("You have no upcoming bookings.")
            return

        embed = discord.Embed(
            title="Upcoming Bookings",
            color=discord.Color.blue(),
        )
        for booking in bookings:
            embed.add_field(
                name=f"{booking.simple_name} at {booking.venue}",
                value=f"**ID:** {booking.id}\n**Date:** {booking.date}\n**Time:** {booking.time}",
                inline=False,
            )
        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"Error listing bookings: {e}", exc_info=True)
        await interaction.followup.send(
            "Sorry, something went wrong while fetching your bookings."
        )


@tree.command(name="list-jobs", description="List scheduled jobs")
async def list_jobs(interaction: discord.Interaction):
    """Slash command to list scheduled jobs."""
    await interaction.response.defer(ephemeral=True)
    try:
        jobs = scheduler.get_jobs()
        if not jobs:
            await interaction.followup.send("There are no scheduled jobs.")
            return

        embed = discord.Embed(
            title="Scheduled Jobs",
            color=discord.Color.green(),
        )
        for job in jobs:
            next_run = (
                job.next_run_time.strftime("%Y-%m-%d %H:%M:%S %Z")
                if job.next_run_time
                else "N/A"
            )
            embed.add_field(
                name=job.name,
                value=f"**Next Run:** {next_run}",
                inline=False,
            )
        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"Error listing jobs: {e}", exc_info=True)
        await interaction.followup.send(
            "Sorry, something went wrong while fetching the jobs."
        )


@tree.command(name="get-config", description="Display the application configuration")
async def get_config(interaction: discord.Interaction):
    """Slash command to display the current application configuration."""
    await interaction.response.defer(ephemeral=True)
    try:
        # Dump Pydantic model to JSON, which redacts SecretStr fields
        config_json = config.model_dump_json(indent=2)
        config_dict = json.loads(config_json)

        # Convert dictionary to YAML
        config_yaml = yaml.dump(config_dict, indent=2, default_flow_style=False)

        # Send as a formatted code block
        message = f"```yaml\n{config_yaml}\n```"

        # Discord has a 2000 character limit per message
        if len(message) > 2000:
            await interaction.followup.send(
                "The configuration is too large to display. "
                "Consider a future enhancement to send it as a file."
            )
        else:
            await interaction.followup.send(message)

    except Exception as e:
        logger.error(f"Error getting configuration: {e}", exc_info=True)
        await interaction.followup.send(
            "Sorry, something went wrong while fetching the configuration."
        )


def start_scheduler(app_config: AppConfig):
    """Add jobs to the scheduler and start it."""
    if not app_config.bookings:
        logger.warning("No bookings configured. Scheduler will not be started.")
        return

    # Validate credentials before starting scheduler
    validate_credentials(app_config.bookings)

    for booking in app_config.bookings:
        cron_kwargs = parse_cron_expression(booking.schedule)
        trigger = CronTrigger(**cron_kwargs, timezone="Europe/London")

        scheduler.add_job(
            run_scheduled_booking,
            trigger=trigger,
            args=[booking],
            id=booking.name,
            name=booking.name,
        )
        now = datetime.datetime.now(ZoneInfo("Europe/London"))
        next_run = trigger.get_next_fire_time(None, now)
        booking_date = (
            next_run.date() if next_run else datetime.date.today()
        ) + datetime.timedelta(days=booking.days_ahead)
        logger.info(
            f"Scheduled job: {booking.name} (next run: {next_run}, booking for: {booking_date})"
        )

    scheduler.start()
    logger.info(f"Scheduler started with {len(app_config.bookings)} job(s).")


@client.event
async def on_ready():
    """Event handler for when the bot is ready."""
    await tree.sync()
    logger.info(f"Logged in as {client.user}")
    logger.info("Discord bot is ready and commands are synced.")


async def main():
    """Main entry point for the application."""
    if not config.discord_bot:
        raise ValueError("Discord bot configuration is missing.")

    # Initialize and start the scheduler
    start_scheduler(config)

    # Start the Discord bot
    token = config.discord_bot.token.get_secret_value()
    await client.start(token)


if __name__ == "__main__":
    asyncio.run(main())
