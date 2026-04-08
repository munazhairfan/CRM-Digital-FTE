"""
FlowForge FTE — Background Scheduler
Handles recurring tasks like the Daily Report.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from production.services.daily_report_service import DailyReportService
import logging

log = logging.getLogger("apscheduler")

scheduler = AsyncIOScheduler()

async def scheduled_daily_report():
    """
    This function is called automatically by the scheduler every day at 9:00 AM.
    """
    print("⏰ CRON TRIGGER: Generating Daily Report...")
    reporter = DailyReportService()
    result = await reporter.generate_and_send(days=1)
    if result.get("status") == "sent":
        print(f"✅ Scheduled Report sent to {result.get('recipient')}")
    else:
        print(f"❌ Scheduled Report failed: {result.get('error')}")

def start_scheduler():
    """
    Configures the schedule and starts the background thread.
    """
    # Add Job: Every day at 09:00 AM (Production Mode)
    scheduler.add_job(
        scheduled_daily_report, 
        'cron', 
        hour=9, 
        minute=0,
        id='daily_sentiment_report',
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    print("🚀 Background Scheduler Started — Daily Report set for 09:00 AM daily.")

def stop_scheduler():
    """
    Gracefully shuts down the scheduler.
    """
    if scheduler.running:
        scheduler.shutdown()
        print("🛑 Scheduler Shutdown.")
