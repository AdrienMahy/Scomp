"""Automation module for smart scraping"""
from .smart_scraper import SmartScraper
from .monitor import ScrapingMonitor
from .scheduler_config import AutomationConfig

__all__ = ["SmartScraper", "ScrapingMonitor", "AutomationConfig"]
