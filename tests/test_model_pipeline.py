"""Data generator + feature engineering tests."""
import pandas as pd

from model.training.data_generator import generate_dataset


class TestDataGenerator:
    def test_generates_correct_row_count(self):
        assert len(generate_dataset(n=300)) == 300

    def test_all_triage_levels_present(self):
        assert set(generate_dataset(n=1000)["triage_level"].unique()) == {0, 1, 2, 3}

    def test_vital_ranges(self):
        df = generate_dataset(n=500)
        assert df["age"].between(1, 100).all()
        assert df["oxygen_saturation"].between(70, 100).all()
        assert df["heart_rate"].between(30, 220).all()

    def test_diastolic_below_systolic(self):
        df = generate_dataset(n=800).dropna(subset=["diastolic_bp"])
        assert (df["diastolic_bp"] < df["systolic_bp"]).all()

    def test_is_reproducible(self):
        pd.testing.assert_frame_equal(generate_dataset(200, seed=7), generate_dataset(200, seed=7))


class TestFeatureEngineering:
    def setup_method(self):
        self.df = generate_dataset(n=200)

    def test_shock_index_formula(self):
        from model.train import engineer_features
        r = engineer_features(self.df)
        pd.testing.assert_series_equal(r["shock_index"], (r["heart_rate"] / r["systolic_bp"]).round(3),
                                       check_names=False)

    def test_fever_flag_threshold(self):
        from model.train import engineer_features
        r = engineer_features(self.df)
        assert (r[r["temperature"] > 38.0]["fever_flag"] == 1).all()

    def test_hypoxia_flag_threshold(self):
        from model.train import engineer_features
        r = engineer_features(self.df)
        assert (r[r["oxygen_saturation"] < 94]["hypoxia_flag"] == 1).all()

    def test_all_derived_cols_created(self):
        from model.train import engineer_features
        r = engineer_features(self.df)
        for col in ["shock_index", "map_mmhg", "pulse_pressure", "fever_flag", "hypoxia_flag", "tachycardia_flag"]:
            assert col in r.columns, f"Missing: {col}"

    def test_missing_values_do_not_crash(self):
        from model.train import engineer_features
        assert engineer_features(self.df[self.df.isna().any(axis=1)]).shape[0] > 0


def test_training_works_from_a_fresh_checkout(tmp_path, monkeypatch):
    """Regression: Render/CI/Docker start with NO data/, assets/ or artifacts/ folders — training must create them."""
    from model.training import config as C
    monkeypatch.setattr(C, "RAW_DATA_PATH", tmp_path / "data" / "raw" / "triage_dataset.csv")
    monkeypatch.setattr(C, "PROC_DATA_PATH", tmp_path / "data" / "processed" / "triage_processed.csv")
    monkeypatch.setattr(C, "ARTIFACT_DIR", tmp_path / "model" / "artifacts")
    monkeypatch.setattr(C, "ASSETS_DIR", tmp_path / "assets")
    from model.train import train
    metrics = train(300, 10, 2, make_plots=False, verbose=False)
    assert metrics["accuracy"] > 0.5
    assert (tmp_path / "data" / "processed" / "triage_processed.csv").exists()
    assert (tmp_path / "model" / "artifacts" / "triage_model.pkl").exists()
    assert (tmp_path / "assets" / "metrics.json").exists()
