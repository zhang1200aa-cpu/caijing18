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
    generate_today_summary,
    generate_yesterday_summary,
    generate_3d_summary,
    generate_1w_summary,
    generate_search_summary,
    get_summary_status,
)
from .admin_service import (
    sync_config_channels_to_db,
    ensure_secret_key,
    get_scrape_interval_minutes,
    reschedule_scrape_job,
    init_scheduler,
    get_summary_schedule,
    update_summary_schedule,
)

# 向后兼容别名
generate_summary_for_range = generate_today_summary
generate_merged_summary_for_range = generate_3d_summary

__all__ = [
    'news_to_dict', 'get_news_list', 'get_news_detail', 'search_news', 'get_tags', 'get_stats',
    'generate_today_summary', 'generate_yesterday_summary', 'generate_3d_summary',
    'generate_1w_summary', 'generate_search_summary', 'get_summary_status',
    'generate_summary_for_range', 'generate_merged_summary_for_range',
    'sync_config_channels_to_db', 'ensure_secret_key',
    'get_scrape_interval_minutes', 'reschedule_scrape_job', 'init_scheduler',
    'get_summary_schedule', 'update_summary_schedule',
]