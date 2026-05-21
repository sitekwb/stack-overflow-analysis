from app.data_loader import load_data


def test_load_data_nonempty():
    df = load_data()
    assert len(df) > 1000
    assert "converted_comp_yearly" in df.columns
