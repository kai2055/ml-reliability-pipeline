from src.monitoring.drift_detector import FeatureDriftResult
from src.monitoring.report_generator import generate_report


def test_summary_counts():
    sig = FeatureDriftResult("loan_amount", "numerical", psi=0.30, wasserstein=0.9)
    mod = FeatureDriftResult("interest_rate", "numerical", psi=0.15, wasserstein=0.2)
    low = FeatureDriftResult("loan_type", "categorical", psi=0.05, wasserstein=None)

    report = generate_report([sig, mod, low])

    assert report.summary.significant == 1
    assert report.summary.moderate == 1
    assert report.summary.low == 1



def test_total_features():
    sig = FeatureDriftResult("loan_amount", "numerical", psi=0.30, wasserstein=0.9)
    mod = FeatureDriftResult("interest_rate", "numerical", psi=0.15, wasserstein=0.2)
    low = FeatureDriftResult("loan_type", "categorical", psi=0.05, wasserstein=None)

    report = generate_report([sig, mod, low])

    assert report.summary.total_features == 3


def test_details_sorted_worst_first():
      sig = FeatureDriftResult("loan_amount", "numerical", psi=0.30, wasserstein=0.9)
      mod = FeatureDriftResult("interest_rate", "numerical", psi=0.15, wasserstein=0.2)
      low = FeatureDriftResult("loan_type", "categorical", psi=0.05, wasserstein=None)

      report = generate_report([low, sig, mod])     # passed in wrong order

      assert report.details[0].feature_name == "loan_amount"
      assert report.details[1].feature_name == "interest_rate"
      assert report.details[2].feature_name == "loan_type"


def test_categorical_has_no_wasserstein():
     low = FeatureDriftResult("loan_type", "categorical", psi=0.05, wasserstein=None)
     report = generate_report([low])

     detail = report.details[0]
     assert detail.wasserstein is None
     assert detail.wasserstein is None
