"""
FlowForge FTE — Daily Report Service
Orchestrates data fetching, HTML rendering, and email delivery.
"""
import os
import datetime
from production.services.reporting_service import ReportingService
from production.services.report_template import render_report_html
from production.ingestion.gmail import GmailIngestion

class DailyReportService:
    def __init__(self):
        self.reporting = ReportingService()
        self.gmail = GmailIngestion()
        self.admin_email = os.getenv("REPORT_ADMIN_EMAIL", "admin@flowforge.com")

    async def generate_and_send(self, days: int = 1):
        """
        1. Fetches sentiment data from DB
        2. Renders HTML template
        3. Sends email via Gmail API
        """
        print(f"📊 Generating daily report for last {days} day(s)...")
        
        # 1. Fetch Data
        report_data = await self.reporting.get_sentiment_report(days=days)
        
        # 2. Render HTML
        html_content = render_report_html(report_data)
        
        # 3. Send Email
        subject = f"📊 Daily FTE Report - {datetime.date.today().isoformat()} - Score: {report_data['summary']['daily_average_sentiment']}"
        
        try:
            await self.gmail.send_reply(
                to_email=self.admin_email,
                subject=subject,
                body=html_content,
                is_html=True
            )
            print(f"✅ Report sent to {self.admin_email}")
            return {"status": "sent", "recipient": self.admin_email}
        except Exception as e:
            print(f"❌ Failed to send report: {e}")
            return {"status": "failed", "error": str(e)}
