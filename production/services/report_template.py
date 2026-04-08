"""
FlowForge FTE — Report HTML Template
Generates a responsive, email-compatible HTML report.
"""

def render_report_html(report_data: dict) -> str:
    """
    Transforms the JSON report data into a beautiful HTML email.
    """
    summary = report_data.get("summary", {})
    by_channel = report_data.get("by_channel", [])
    at_risk = report_data.get("at_risk_customers", [])
    
    # --- Calculations ---
    total = summary.get("total_interactions", 0)
    avg_sentiment = summary.get("daily_average_sentiment", 0.0)
    pos = summary.get("breakdown", {}).get("positive", 0)
    neg = summary.get("breakdown", {}).get("negative", 0)
    
    # Sentiment Color
    if avg_sentiment >= 0.6:
        sent_color = "#10b981" # Green
    elif avg_sentiment >= 0.4:
        sent_color = "#f59e0b" # Orange
    else:
        sent_color = "#ef4444" # Red

    # Progress Bar Width
    pos_pct = (pos / total * 100) if total else 0
    neg_pct = (neg / total * 100) if total else 0

    # --- HTML Template ---
    return f"""
    <div style="font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f3f4f6; margin: 0; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            
            <!-- Header -->
            <div style="background-color: #1f2937; padding: 24px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">🤖 FlowForge FTE Report</h1>
                <p style="color: #9ca3af; margin: 5px 0 0 0; font-size: 14px;">Daily Performance Summary</p>
            </div>

            <!-- KPI Cards -->
            <div style="display: flex; gap: 10px; padding: 20px;">
                <div style="flex: 1; background: #f9fafb; padding: 15px; border-radius: 6px; text-align: center;">
                    <div style="font-size: 28px; font-weight: bold; color: #111827;">{total}</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 1px;">Interactions</div>
                </div>
                <div style="flex: 1; background: #f9fafb; padding: 15px; border-radius: 6px; text-align: center;">
                    <div style="font-size: 28px; font-weight: bold; color: {sent_color};">{avg_sentiment:.2f}</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 1px;">Avg Sentiment</div>
                </div>
                <div style="flex: 1; background: #f9fafb; padding: 15px; border-radius: 6px; text-align: center;">
                    <div style="font-size: 28px; font-weight: bold; color: #6b7280;">{len(at_risk)}</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 1px;">At Risk</div>
                </div>
            </div>

            <!-- Sentiment Bar -->
            <div style="padding: 0 20px 20px 20px;">
                <div style="background: #e5e7eb; height: 10px; border-radius: 5px; overflow: hidden;">
                    <div style="width: {pos_pct}%; background: #10b981; height: 100%; float: left;"></div>
                    <div style="width: {neg_pct}%; background: #ef4444; height: 100%; float: right;"></div>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 11px; color: #6b7280; margin-top: 5px;">
                    <span>Positive ({pos})</span>
                    <span>Negative ({neg})</span>
                </div>
            </div>

            <!-- Channel Table -->
            <div style="padding: 0 20px 20px 20px;">
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead>
                        <tr style="border-bottom: 2px solid #e5e7eb; text-align: left;">
                            <th style="padding: 8px;">Channel</th>
                            <th style="padding: 8px;">Volume</th>
                            <th style="padding: 8px;">Sentiment</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([
                            f"<tr style='border-bottom: 1px solid #f3f4f6;'>"
                            f"<td style='padding: 8px; font-weight: bold;'>{r['channel'].capitalize()}</td>"
                            f"<td style='padding: 8px;'>{r['count']}</td>"
                            f"<td style='padding: 8px; color: {'#10b981' if r['avg_sentiment'] > 0.6 else '#ef4444'};'>{r['avg_sentiment']:.2f}</td>"
                            f"</tr>" 
                            for r in by_channel
                        ])}
                    </tbody>
                </table>
            </div>

            <!-- At Risk Customers -->
            <div style="padding: 20px; background-color: #fef2f2; border-top: 1px solid #fee2e2;">
                <h3 style="color: #991b1b; margin: 0 0 10px 0; font-size: 16px;">⚠️ At-Risk Customers (Score ≤ 0.3)</h3>
                <ul style="margin: 0; padding-left: 20px; color: #7f1d1d;">
                    {"".join([
                        f"<li style='margin-bottom: 4px;'><strong>{c['name']}</strong> ({c['channel']}) — Last Score: {c['latest_sentiment']:.2f}</li>" 
                        for c in at_risk
                    ]) or '<li>No critical issues found today.</li>'}
                </ul>
            </div>

            <!-- Footer -->
            <div style="background-color: #f9fafb; padding: 15px; text-align: center; font-size: 12px; color: #9ca3af;">
                FlowForge Customer Success Digital FTE &copy; 2026
            </div>
        </div>
    </div>
    """
