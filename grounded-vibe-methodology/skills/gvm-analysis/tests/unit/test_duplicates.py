"""Tests for ``_shared/duplicates.py`` — AN-16 (TC-AN-16-01..04)."""

from __future__ import annotations

import pandas as pd

from _shared import duplicates


# ---------------------------------------------------------------------------
# Contract shape
# ---------------------------------------------------------------------------


def test_find_exact_contract_shape() -> None:
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    result = duplicates.find_exact(df)
    assert isinstance(result, list)
    assert len(result) == 1
    assert set(result[0]) == {"row_indices", "n_duplicates"}
    assert isinstance(result[0]["row_indices"], list)
    assert all(isinstance(i, int) for i in result[0]["row_indices"])
    assert isinstance(result[0]["n_duplicates"], int)


def test_find_near_contract_shape() -> None:
    s = pd.Series(["Acme Corp", "Acme Corp ", "Other"])
    result = duplicates.find_near(s, "name")
    assert isinstance(result, list)
    if result:
        entry = result[0]
        assert set(entry) == {"key_column", "cluster", "similarity"}
        assert entry["key_column"] == "name"
        assert isinstance(entry["cluster"], list)
        for member in entry["cluster"]:
            assert set(member) == {"row_index", "value"}
            assert isinstance(member["row_index"], int)
            assert isinstance(member["value"], str)
        assert isinstance(entry["similarity"], float)


# ---------------------------------------------------------------------------
# TC-AN-16-01 — exact-row duplicates
# ---------------------------------------------------------------------------


def test_tc_an_16_01_five_duplicate_pairs() -> None:
    # 990 unique + 5 pairs of identical rows = 1000 rows
    base = pd.DataFrame(
        {
            "a": list(range(990))
            + [10000, 10000, 20000, 20000, 30000, 30000, 40000, 40000, 50000, 50000],
            "b": ["u" + str(i) for i in range(990)]
            + ["dA", "dA", "dB", "dB", "dC", "dC", "dD", "dD", "dE", "dE"],
        }
    )
    assert len(base) == 1000
    result = duplicates.find_exact(base)
    assert len(result) == 5
    for group in result:
        assert group["n_duplicates"] == 2
        assert len(group["row_indices"]) == 2


def test_find_exact_triple_reports_n_3() -> None:
    df = pd.DataFrame({"a": [1, 1, 1, 2, 3], "b": ["x", "x", "x", "y", "z"]})
    result = duplicates.find_exact(df)
    assert len(result) == 1
    assert result[0]["n_duplicates"] == 3
    assert sorted(result[0]["row_indices"]) == [0, 1, 2]


# ---------------------------------------------------------------------------
# TC-AN-16-02 — near-duplicates on key column
# ---------------------------------------------------------------------------


def test_tc_an_16_02_acme_variants_clustered() -> None:
    values = [
        "Acme Corporation",
        "Acme Corporation ",
        "ACME Corp",
        "Acme Corp.",
        "Globex Inc",
    ]
    s = pd.Series(values)
    result = duplicates.find_near(s, "customer_name")
    # Expect at least one cluster containing the four Acme variants.
    assert len(result) >= 1
    acme_cluster = max(result, key=lambda c: len(c["cluster"]))
    member_indices = [m["row_index"] for m in acme_cluster["cluster"]]
    assert set(member_indices) >= {0, 1, 2, 3}
    assert "Globex Inc" not in [m["value"] for m in acme_cluster["cluster"]]
    assert acme_cluster["key_column"] == "customer_name"
    # Loose lower bound — the threshold is 0.85, and the reported similarity is
    # the minimum pairwise within the cluster, which depends on scorer internals
    # and can vary across rapidfuzz versions. Assert a stable floor well below
    # the threshold; cluster membership above is the actual correctness check.
    assert acme_cluster["similarity"] > 0.80


def test_find_near_singleton_not_reported() -> None:
    s = pd.Series(["Alpha", "Zulu", "Omega"])
    result = duplicates.find_near(s, "name")
    assert result == []


def test_find_near_boundary_threshold() -> None:
    # Two identical strings cluster at any threshold ≤ 1.0.
    s = pd.Series(["same", "same", "different entirely"])
    result = duplicates.find_near(s, "name", threshold=1.0)
    assert len(result) == 1
    assert result[0]["similarity"] == 1.0


# ---------------------------------------------------------------------------
# TC-AN-16-03 — auto-detected key column
# ---------------------------------------------------------------------------


def test_tc_an_16_03_auto_detect_high_cardinality_string() -> None:
    df = pd.DataFrame(
        {
            "status": ["active"] * 50 + ["inactive"] * 50,  # low cardinality
            "customer_name": [
                f"Customer_{i}" for i in range(100)
            ],  # high cardinality string
            "amount": list(range(100)),  # numeric
        }
    )
    picked = duplicates.auto_detect_key(df)
    assert picked == "customer_name"


def test_auto_detect_returns_none_when_no_string_column() -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]})
    assert duplicates.auto_detect_key(df) is None


def test_auto_detect_returns_none_when_all_strings_low_cardinality() -> None:
    df = pd.DataFrame({"category": ["a", "b", "a", "b"] * 25})
    assert duplicates.auto_detect_key(df) is None


# ---------------------------------------------------------------------------
# TC-AN-16-04 — empty file
# ---------------------------------------------------------------------------


def test_tc_an_16_04_empty_dataframe_exact() -> None:
    df = pd.DataFrame(
        {"a": pd.Series([], dtype="int64"), "b": pd.Series([], dtype="object")}
    )
    assert duplicates.find_exact(df) == []


def test_tc_an_16_04_empty_series_near() -> None:
    s = pd.Series([], dtype="object")
    assert duplicates.find_near(s, "name") == []


def test_tc_an_16_04_empty_dataframe_auto_detect() -> None:
    df = pd.DataFrame({"a": pd.Series([], dtype="object")})
    assert duplicates.auto_detect_key(df) is None


# ---------------------------------------------------------------------------
# Degenerate inputs
# ---------------------------------------------------------------------------


def test_find_exact_no_duplicates_returns_empty() -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    assert duplicates.find_exact(df) == []


def test_find_near_all_null_returns_empty() -> None:
    s = pd.Series([None, None, None], dtype="object")
    assert duplicates.find_near(s, "name") == []


def test_find_near_single_value_returns_empty() -> None:
    s = pd.Series(["only"])
    assert duplicates.find_near(s, "name") == []


def test_find_near_invalid_threshold_raises() -> None:
    import pytest

    s = pd.Series(["a", "b"])
    with pytest.raises(ValueError):
        duplicates.find_near(s, "name", threshold=1.5)
    with pytest.raises(ValueError):
        duplicates.find_near(s, "name", threshold=0.4)


def test_find_near_all_identical_values() -> None:
    """All-identical series → single cluster with similarity == 1.0."""
    s = pd.Series(["same", "same", "same"])
    result = duplicates.find_near(s, "name")
    assert len(result) == 1
    assert result[0]["similarity"] == 1.0
    assert len(result[0]["cluster"]) == 3


def test_find_near_deterministic_ordering() -> None:
    s = pd.Series(["Acme", "Acme ", "Zulu", "Zulu "])
    result = duplicates.find_near(s, "name")
    # Clusters should be sorted by smallest row_index (0 → Acme before 2 → Zulu).
    assert len(result) == 2
    first_min = min(m["row_index"] for m in result[0]["cluster"])
    second_min = min(m["row_index"] for m in result[1]["cluster"])
    assert first_min < second_min
