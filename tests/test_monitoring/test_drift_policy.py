
from src.monitoring.drift_policy import classify_severity



def test_classify_low():
    assert classify_severity(0.05, moderate=0.1, significant=0.25) == "low"

def test_classify_moderate():
    assert classify_severity(0.15, moderate=0.1, significant=0.25) == "moderate"


def test_classify_significant():
    assert classify_severity(0.30, moderate=0.1, significant=0.25) == "significant"

