from __future__ import annotations

import json

import pandas as pd

from riskripple.api.handlers.ingest import _serialize_fred_observations


def test_serialize_fred_observations_is_json_safe():
    # Regression: json.dumps(series.to_dict()) raised "keys must be str, int, float,
    # bool or None, not Timestamp" the first time this handler actually ran against
    # live data (pandas Series with a DatetimeIndex) -- every prior test used a
    # fixture that never produced this shape.
    series = pd.Series([4.5, 4.6], index=pd.to_datetime(["2026-01-02", "2026-01-03"]))

    result = _serialize_fred_observations(series)

    assert result == {"2026-01-02T00:00:00": 4.5, "2026-01-03T00:00:00": 4.6}
    json.dumps(result)  # must not raise
