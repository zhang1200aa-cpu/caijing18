"""
caijing18 服务层
"""
from .news_service import (
    news_to_dict,
    get_news_list,
    get_news_detail,
    search_news,
    get_tags,
    get_stats,
)
from .summary_service import (
    generate_summary_for_range,
    generate_merged_summary_for_range,
    get_date_range,
    get_news_dicts_in_range,
    get_range_news_count,
)
from .admin_service import (
    sync_config_channels_to_db,
    ensure_secret_key,
    get_scrape_interval_minutes,
    reschedule_scrape_job,
    init_scheduler,
)

__all__ = [
    'news_to_dict', 'get_news_list', 'get_news_detail', 'search_news', 'get_tags', 'get_stats',
    'generate_summary_for_range', 'generate_merged_summary_for_range',
    'get_date_range', 'get_news_dicts_in_range', 'get_range_news_count',
    'sync_config_channels_to_db', 'ensure_secret_key',
    'get_scrape_interval_minutes', 'reschedule_scrape_job', 'init_scheduler',
]
