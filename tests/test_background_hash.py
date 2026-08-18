from aapforge.aap.hash import background_hash


def test_background_hash_known_values():
    assert background_hash("BG_Black") == 1047754314
    assert background_hash("BG_GameDevRoom") == 1194944144
    assert background_hash("BG_Mist_L") == 1407749724
