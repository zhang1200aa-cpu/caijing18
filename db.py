#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库 Session 上下文管理器
消除各部门中重复的 try/finally/session.close() 代码
"""
import logging
from contextlib import contextmanager
from database import get_session

logger = logging.getLogger(__name__)


@contextmanager
def session_scope():
    """数据库 Session 上下文管理器，自动提交和关闭"""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"数据库操作失败，已回滚: {e}")
        raise
    finally:
        session.close()


@contextmanager
def session_scope_readonly():
    """只读数据库 Session 上下文管理器（不提交）"""
    session = get_session()
    try:
        yield session
    except Exception as e:
        logger.error(f"数据库只读操作失败: {e}")
        raise
    finally:
        session.close()