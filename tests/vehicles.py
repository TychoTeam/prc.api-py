from typing import List, Tuple, get_args
import re

from prc import VehicleModel, VehicleName


YEAR_RE = re.compile(r"^\d{4}\s+")


def name_to_model(name: str) -> str:
    return YEAR_RE.sub("", name)


def model_to_name_candidates(
    model: str,
    names: Tuple[str, ...],
) -> List[str]:
    return [name for name in names if name_to_model(name) == model]


def test_models():
    names = get_args(VehicleName)
    models = set(get_args(VehicleModel))

    for model in models:
        matching_names = model_to_name_candidates(model, names)

        assert matching_names, f'Model "{model}" has no matching vehicle name'


def test_names():
    names = get_args(VehicleName)
    models = get_args(VehicleModel)

    for name in names:
        normalized = name_to_model(name)

        assert normalized in models, (
            f'Name "{name}" has no matching vehicle model ' f'"{normalized}"'
        )


def test_relationship():
    names = get_args(VehicleName)
    models = get_args(VehicleModel)

    for model in models:
        matching_names = model_to_name_candidates(model, names)

        assert matching_names, f'Model "{model}" has no matching names'

        for name in matching_names:
            assert (
                name_to_model(name) == model
            ), f'Name "{name}" does not normalize to model "{model}"'


test_models()
test_names()
test_relationship()
