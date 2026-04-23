from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

def kst_now() -> datetime:
    return datetime.now(KST)
