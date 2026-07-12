from copy import deepcopy

from src.config.settings import default_settings
from src.utils import merge_json


def test_legacy_inventory_filters_gain_new_keys_without_resetting_choices():
    legacy_settings = deepcopy(default_settings)
    legacy_filters = legacy_settings["inventory_filters"]
    del legacy_filters["show_linked_only"]
    del legacy_filters["show_unfinished_only"]
    legacy_filters["show_not_linked"] = False
    legacy_filters["show_finished"] = True

    merge_json(legacy_settings, default_settings)

    merged_filters = legacy_settings["inventory_filters"]
    assert merged_filters["show_not_linked"] is False
    assert merged_filters["show_finished"] is True
    assert merged_filters["show_linked_only"] is False
    assert merged_filters["show_unfinished_only"] is False
