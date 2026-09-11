@echo off
title YouTube Automation Agent (24/7 Autonomous Daemon)
cd /d D:\youtube_automation_agent
echo Starting YouTube Automation Agent Watchdog...
python pipeline_watchdog.py
pause
