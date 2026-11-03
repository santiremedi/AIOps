import pandas as pd

from anomaly_detection.chaos_labels import label_by_scenario, load_chaos_log

TIMESTAMPS = pd.Series(pd.date_range("2026-01-01 08:00", periods=8, freq="min", tz="UTC"))


def test_load_chaos_log_parses_utc_times(tmp_path):
    path = tmp_path / "chaos-log.csv"
    path.write_text("scenario,start,end\ncpu_users,2026-01-01T08:01:00Z,2026-01-01T08:02:00Z\n")

    chaos_log = load_chaos_log(path)

    assert chaos_log.loc[0, "start"] == pd.Timestamp("2026-01-01 08:01", tz="UTC")


def test_labels_the_active_scenario_and_extends_it_by_the_effect_tail():
    chaos_log = pd.DataFrame({
        "scenario": ["cpu_users", "db_freeze"],
        "start": pd.to_datetime(["2026-01-01 08:01", "2026-01-01 08:05"], utc=True),
        "end": pd.to_datetime(["2026-01-01 08:02", "2026-01-01 08:06"], utc=True),
    })

    labels = label_by_scenario(TIMESTAMPS, chaos_log, effect_tail=pd.Timedelta(minutes=1))

    assert labels.tolist() == [
        "normal", "cpu_users", "cpu_users", "normal", "normal", "db_freeze", "db_freeze", "normal",
    ]
