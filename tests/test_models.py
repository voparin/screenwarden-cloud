from cloud.db.models import Family, Device, ChildUser, DailyUsageMirror, Command, ConfigMirror, PairingCode

def test_models_importable():
    assert Family.__tablename__ == "families"
    assert Device.__tablename__ == "devices"
    assert ChildUser.__tablename__ == "child_users"
    assert DailyUsageMirror.__tablename__ == "daily_usage_mirror"
    assert Command.__tablename__ == "commands"
    assert ConfigMirror.__tablename__ == "config_mirror"
    assert PairingCode.__tablename__ == "pairing_codes"
